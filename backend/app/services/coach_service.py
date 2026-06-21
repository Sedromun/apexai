from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.coach.payload import build_coach_payload, validate_result
from app.coach.providers import CoachError, CoachProvider, CoachResult, get_coach_provider
from app.core.config import settings
from app.core.errors import (
    CoachUnavailableError,
    NotFoundError,
    PaymentRequiredError,
    ValidationAppError,
)
from app.models.coach_report import CoachReport
from app.models.user import User
from app.repositories.coach_repo import CoachReportRepository
from app.repositories.lap_repo import LapRepository
from app.schemas.coach import TrajectoryLesson
from app.services import track_catalog
from app.storage.object_store import ObjectStore
from app.telemetry.compare import compute_delta
from app.telemetry.metrics import compute_lap_metrics
from app.telemetry.trace import LapTrace

logger = logging.getLogger(__name__)


class CoachService:
    def __init__(
        self, db: AsyncSession, store: ObjectStore, provider: CoachProvider | None = None
    ) -> None:
        self.db = db
        self.store = store
        self.reports = CoachReportRepository(db)
        self.laps = LapRepository(db)
        self.provider = provider or get_coach_provider()

    async def analyze(self, user: User, lap_id: uuid.UUID, *, force: bool = False) -> CoachReport:
        lap = await self.laps.get_for_user(lap_id, user.id)
        if lap is None:
            raise NotFoundError("Lap not found", code="lap_not_found")

        # Cache: one report per lap. Returning it never consumes a new analysis. `force`
        # regenerates (e.g. the "Перегенерировать" button) and replaces the old report.
        existing = await self.reports.get_for_lap(lap.id)
        if existing is not None and not force:
            return existing

        used = await self.reports.count_for_user(user.id) - (1 if existing else 0)
        self._enforce_plan_limit(user, used)

        if lap.trace is None:
            raise ValidationAppError("Lap has no telemetry to analyze", code="no_trace")

        metrics = lap.metrics
        self_trace = LapTrace.from_gzip(await self.store.get(lap.trace.storage_key))
        if not metrics:
            metrics = compute_lap_metrics(self_trace)

        delta = await self._delta_to_reference(user, lap, self_trace)
        previous = await self._previous_lesson(user, lap)
        payload = build_coach_payload(
            track=lap.session.track,
            car=lap.session.car_or_team,
            metrics=metrics,
            delta=delta,
            previous=previous,
        )

        # Generate first; only if it succeeds do we replace the old report (a failed
        # regenerate leaves the previous one intact).
        result = await self._generate(payload)
        # Carry the computed data so the next lap's review can compare against this one.
        result.corner_deltas = payload.get("corner_deltas", {})
        result.lap_time_s = payload.get("lap_time_s")
        if existing is not None:
            await self.reports.delete(existing.id)
        report = await self.reports.create(
            lap_id=lap.id,
            summary=result.to_dict(),
            body=result.to_body_markdown(),
            model=result.model,
        )
        await self.db.commit()
        return report

    async def get_report(self, user: User, report_id: uuid.UUID) -> CoachReport:
        report = await self.reports.get_for_user(report_id, user.id)
        if report is None:
            raise NotFoundError("Report not found", code="report_not_found")
        return report

    async def get_report_for_lap(self, user: User, lap_id: uuid.UUID) -> CoachReport:
        lap = await self.laps.get_for_user(lap_id, user.id)
        if lap is None:
            raise NotFoundError("Lap not found", code="lap_not_found")
        report = await self.reports.get_for_lap(lap.id)
        if report is None:
            raise NotFoundError("No report for this lap", code="report_not_found")
        return report

    async def get_trajectory(self, user: User) -> list[TrajectoryLesson]:
        """The user's learning trajectory: every lesson with its lap/track context, oldest→newest."""
        rows = await self.reports.list_for_user(user.id)
        return [
            TrajectoryLesson(
                report_id=r.id,
                lap_id=r.lap_id,
                track=r.track,
                game=r.game,
                lap_time_ms=r.lap_time_ms,
                recorded_at=r.recorded_at,
                summary=r.summary,
            )
            for r in rows
        ]

    def _enforce_plan_limit(self, user: User, used: int) -> None:
        if user.plan == "pro":
            return
        if used >= settings.free_ai_trial:
            raise PaymentRequiredError(
                "AI coach is a Pro feature; the free trial is used up",
                code="upgrade_required",
                details={"free_ai_trial": settings.free_ai_trial, "used": used},
            )

    async def _delta_to_reference(self, user, lap, self_trace: LapTrace):
        # Prefer the stable track эталон (modeled/real ideal lap): its per-corner deltas are
        # comparable across sessions, so progress is measurable. Fall back to the user's best lap.
        track_ref = track_catalog.reference_trace(lap.session.track) if lap.session.track else None
        if track_ref is not None:
            return compute_delta(self_trace, track_ref)
        reference = await self.laps.get_best_lap_for_track(
            user.id, lap.session.game, lap.session.track, exclude_lap_id=lap.id
        )
        if reference is None or reference.trace is None:
            return None
        ref_trace = LapTrace.from_gzip(await self.store.get(reference.trace.storage_key))
        return compute_delta(self_trace, ref_trace)

    async def _previous_lesson(self, user: User, lap) -> dict | None:
        """The prior coach report on this track, distilled into review context for the next lesson."""
        prev = await self.reports.get_previous_for_track(
            user.id, lap.session.game, lap.session.track, lap.recorded_at, lap.id
        )
        if prev is None:
            return None
        s = prev.summary or {}
        return {
            "lap_time_s": s.get("lap_time_s"),
            "focus_points": s.get("focus_points", []),
            "corner_deltas": s.get("corner_deltas", {}),
        }

    async def _generate(self, payload) -> CoachResult:
        # The real LLM is the only source of the coach's words — no fabricated fallback. If it
        # fails or returns something ungrounded, surface a clean "retry" error instead of canned
        # text, so the user can regenerate.
        try:
            result = await self.provider.analyze(payload, lang="ru")
            validate_result(result, payload)
            return result
        except CoachError as exc:
            logger.warning("Coach provider unavailable: %s", exc)
            raise CoachUnavailableError(
                "AI-тренер сейчас недоступен. Нажми «Перегенерировать» через пару секунд."
            ) from exc
