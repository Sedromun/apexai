from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    NotFoundError,
    PaymentRequiredError,
    PayloadTooLargeError,
    ValidationAppError,
)
from app.models.lap import Lap
from app.models.race_session import RaceSession
from app.models.telemetry_trace import TelemetryTrace
from app.models.user import User
from app.repositories.lap_repo import LapRepository
from app.repositories.session_repo import SessionRepository
from app.schemas.lap import (
    CompareLapRef,
    LapCompare,
    LapDetail,
    LapListItem,
    LapMeta,
    LapSummary,
    SessionSummary,
    TraceMeta,
)
from app.schemas.track import ReferenceCompare
from app.services import track_catalog
from app.storage.object_store import ObjectStore
from app.telemetry.compare import compute_delta
from app.telemetry.metrics import compute_lap_metrics
from app.telemetry.trace import LapTrace, TraceValidationError

logger = logging.getLogger(__name__)


class LapService:
    def __init__(self, db: AsyncSession, store: ObjectStore) -> None:
        self.db = db
        self.store = store
        self.laps = LapRepository(db)
        self.sessions = SessionRepository(db)

    async def ingest(self, user: User, meta: LapMeta, trace_blob: bytes) -> Lap:
        if len(trace_blob) > settings.max_trace_upload_bytes:
            raise PayloadTooLargeError(
                "Trace exceeds the maximum upload size",
                code="trace_too_large",
                details={"limit_bytes": settings.max_trace_upload_bytes},
            )

        # Idempotency: a re-sent lap (offline queue retry) must not duplicate.
        existing = await self.laps.get_by_client_uuid(meta.client_lap_uuid)
        if existing is not None:
            owned = await self.laps.get_for_user(existing.id, user.id)
            if owned is None:
                raise ValidationAppError(
                    "client_lap_uuid already used", code="duplicate_lap"
                )
            return owned

        await self._enforce_lap_limit(user)

        try:
            trace = LapTrace.from_gzip(trace_blob)
        except TraceValidationError as exc:
            raise ValidationAppError(f"Invalid trace: {exc}", code="invalid_trace") from exc

        session = await self._resolve_session(user, meta)

        lap_id = uuid.uuid4()
        storage_key = f"traces/{user.id}/{lap_id}.json.gz"
        # Store the blob first; if the DB write fails we have an orphan object (cheap),
        # never a DB row pointing at a missing object.
        await self.store.put(
            storage_key, trace_blob, content_type="application/json", content_encoding="gzip"
        )

        metrics = None
        try:
            metrics = compute_lap_metrics(trace)
        except Exception:  # metrics must never block ingestion
            logger.exception("Layer-1 metrics computation failed for lap %s", lap_id)

        lap = await self.laps.create(
            session_id=session.id,
            client_lap_uuid=meta.client_lap_uuid,
            lap_time_ms=meta.lap_time_ms,
            valid=meta.valid,
            sample_count=trace.points,
            recorded_at=meta.recorded_at,
            lap_id=lap_id,
            metrics=metrics,
        )
        self.db.add(
            TelemetryTrace(
                lap_id=lap.id,
                storage_key=storage_key,
                hz=trace.hz,
                points=trace.points,
                size_bytes=len(trace_blob),
            )
        )
        await self.db.commit()
        return lap

    async def _resolve_session(self, user: User, meta: LapMeta) -> RaceSession:
        if meta.client_session_uuid:
            existing = await self.sessions.get_by_client_uuid(meta.client_session_uuid)
            if existing is not None:
                if existing.user_id != user.id:
                    raise ValidationAppError(
                        "session key already used", code="duplicate_session"
                    )
                return existing
        return await self.sessions.create(
            user_id=user.id,
            game=meta.game,
            track=meta.track,
            car_or_team=meta.car_or_team,
            session_type=meta.session_type,
            weather=meta.weather,
            client_session_uuid=meta.client_session_uuid,
            started_at=meta.recorded_at,
        )

    async def _enforce_lap_limit(self, user: User) -> None:
        """Free plan: cap stored laps per calendar month. Pro is unlimited."""
        if user.plan == "pro":
            return
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = await self.laps.count_for_user_since(user.id, month_start)
        if used >= settings.free_monthly_lap_limit:
            raise PaymentRequiredError(
                "Monthly lap limit reached on the free plan",
                code="lap_limit_reached",
                details={"free_monthly_lap_limit": settings.free_monthly_lap_limit, "used": used},
            )

    async def list_sessions(self, user: User) -> list[SessionSummary]:
        rows = await self.sessions.list_for_user_with_aggregates(user.id)
        return [
            SessionSummary(
                id=s.id,
                game=s.game,
                track=s.track,
                car_or_team=s.car_or_team,
                session_type=s.session_type,
                started_at=s.started_at,
                lap_count=lap_count,
                best_lap_time_ms=best_lap_time_ms,
            )
            for (s, lap_count, best_lap_time_ms) in rows
        ]

    async def list_user_laps(self, user: User) -> list[LapListItem]:
        laps = await self.laps.list_for_user(user.id)
        return [
            LapListItem(
                id=lap.id,
                session_id=lap.session_id,
                game=lap.session.game,
                track=lap.session.track,
                car_or_team=lap.session.car_or_team,
                lap_time_ms=lap.lap_time_ms,
                valid=lap.valid,
                recorded_at=lap.recorded_at,
            )
            for lap in laps
        ]

    async def list_session_laps(self, user: User, session_id: uuid.UUID) -> list[LapSummary]:
        session = await self.sessions.get_by_id(session_id)
        if session is None or session.user_id != user.id:
            raise NotFoundError("Session not found", code="session_not_found")
        laps = await self.laps.list_for_session(session_id)
        return [LapSummary.model_validate(lap) for lap in laps]

    async def get_lap_detail(self, user: User, lap_id: uuid.UUID) -> LapDetail:
        lap = await self.laps.get_for_user(lap_id, user.id)
        if lap is None:
            raise NotFoundError("Lap not found", code="lap_not_found")
        trace_meta = None
        if lap.trace is not None:
            trace_meta = TraceMeta(
                schema_version=lap.trace.schema_version,
                hz=lap.trace.hz,
                points=lap.trace.points,
                size_bytes=lap.trace.size_bytes,
            )
        reference = await self.laps.get_best_lap_for_track(
            user.id, lap.session.game, lap.session.track, exclude_lap_id=lap.id
        )
        track_ref = (
            track_catalog.reference_meta(lap.session.track) if lap.session.track else None
        )
        return LapDetail(
            id=lap.id,
            session_id=lap.session_id,
            game=lap.session.game,
            track=lap.session.track,
            car_or_team=lap.session.car_or_team,
            lap_time_ms=lap.lap_time_ms,
            valid=lap.valid,
            sample_count=lap.sample_count,
            recorded_at=lap.recorded_at,
            has_metrics=lap.has_metrics,
            metrics=lap.metrics,
            trace=trace_meta,
            reference_lap_id=reference.id if reference else None,
            track_reference=track_ref,
        )

    async def get_lap_trace(self, user: User, lap_id: uuid.UUID) -> dict:
        lap = await self.laps.get_for_user(lap_id, user.id)
        if lap is None or lap.trace is None:
            raise NotFoundError("Trace not found", code="trace_not_found")
        blob = await self.store.get(lap.trace.storage_key)
        return LapTrace.from_gzip(blob).to_dict()

    async def compare(self, user: User, a_id: uuid.UUID, b_id: uuid.UUID) -> LapCompare:
        lap_a = await self.laps.get_for_user(a_id, user.id)
        lap_b = await self.laps.get_for_user(b_id, user.id)
        if lap_a is None or lap_a.trace is None:
            raise NotFoundError("Lap not found", code="lap_not_found", details={"lap": "a"})
        if lap_b is None or lap_b.trace is None:
            raise NotFoundError("Lap not found", code="lap_not_found", details={"lap": "b"})

        trace_a = LapTrace.from_gzip(await self.store.get(lap_a.trace.storage_key))
        trace_b = LapTrace.from_gzip(await self.store.get(lap_b.trace.storage_key))
        delta = compute_delta(trace_a, trace_b)

        return LapCompare(
            a=CompareLapRef(id=lap_a.id, lap_time_ms=lap_a.lap_time_ms, track=lap_a.session.track),
            b=CompareLapRef(id=lap_b.id, lap_time_ms=lap_b.lap_time_ms, track=lap_b.session.track),
            distance_m=delta["distance_m"],
            delta_s=delta["delta_s"],
            total_delta_s=delta["total_delta_s"],
            corners=delta["corners"],
        )

    async def compare_reference(self, user: User, lap_id: uuid.UUID) -> ReferenceCompare:
        """Compare the caller's lap against the modeled 'ideal lap' for its track."""
        lap = await self.laps.get_for_user(lap_id, user.id)
        if lap is None or lap.trace is None:
            raise NotFoundError("Lap not found", code="lap_not_found")

        track = lap.session.track
        ref_trace = track_catalog.reference_trace(track) if track else None
        ref_meta = track_catalog.reference_meta(track) if track else None
        if ref_trace is None or ref_meta is None:
            raise NotFoundError(
                "No reference lap for this track", code="reference_not_found"
            )

        self_trace = LapTrace.from_gzip(await self.store.get(lap.trace.storage_key))
        delta = compute_delta(self_trace, ref_trace)
        return ReferenceCompare(
            track=track,
            reference_label=ref_meta["label"],
            reference_lap_time_ms=ref_meta["lap_time_ms"],
            self_lap_time_ms=lap.lap_time_ms,
            distance_m=delta["distance_m"],
            delta_s=delta["delta_s"],
            total_delta_s=delta["total_delta_s"],
            corners=delta["corners"],
        )
