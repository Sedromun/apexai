"""Build the compact LLM payload from layer-1 metrics, and validate LLM output against it."""

from __future__ import annotations

from typing import Any

from app.coach.providers import CoachResult, CoachValidationError


def _dist(value: Any, hi: float) -> float | None:
    """Pass a distance metric through only if physically plausible — corner detection can
    occasionally place a brake point a whole sector away; feeding that to the coach makes it
    cite nonsense like 'тормозишь за 2929 м до апекса'. Implausible → null (the model omits it)."""
    return value if isinstance(value, (int, float)) and 0 <= value <= hi else None


def build_coach_payload(
    *,
    track: str | None,
    car: str | None,
    metrics: dict[str, Any],
    delta: dict[str, Any] | None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = metrics.get("summary", {})
    compact_corners = [
        {
            "corner": c["number"],
            "apex_dist_m": c["apex_dist_m"],
            "entry_kmh": c["entry_speed_kmh"],
            "apex_kmh": c["apex_speed_kmh"],
            "exit_kmh": c["exit_speed_kmh"],
            "brake_to_apex_m": _dist(c["brake_to_apex_m"], 400),
            "trail_brake_m": _dist(c["trail_brake_overlap_m"], 250),
            "steer_reversals": c["steering_reversals"],
            "direction": c["direction"],
        }
        for c in metrics.get("corners", [])
    ]

    # A messy captured lap (telemetry gap / non-monotonic distance) can make compute_delta
    # spike a single corner to e.g. 52 s, which is physically impossible, poisons the homework,
    # and trips the anti-hallucination validator so the LLM falls back to the stub. Keep only
    # corner deltas within the same plausibility ceiling the validator uses.
    total_delta = abs((delta or {}).get("total_delta_s") or 0.0)
    plausible_delta = total_delta * 2 + 3.0

    biggest_losses: list[dict[str, Any]] = []
    if delta:
        biggest_losses = sorted(
            (c for c in delta.get("corners", []) if 0.02 < c["delta_s"] <= plausible_delta),
            key=lambda c: c["delta_s"],
            reverse=True,
        )[:3]

    corner_deltas: dict[str, float] = {}
    if delta:
        corner_deltas = {
            str(c["number"]): round(c["delta_s"], 3)
            for c in delta.get("corners", [])
            if abs(c["delta_s"]) <= plausible_delta
        }

    return {
        "track": track,
        "car": car,
        "lap_time_s": round(metrics.get("lap_time_ms", 0) / 1000.0, 3),
        "delta_to_reference_s": delta["total_delta_s"] if delta else None,
        "summary": summary,
        "corners": compact_corners,
        "biggest_losses": biggest_losses,
        "corner_deltas": corner_deltas,
        "previous": previous,  # prior lesson on this track: {lap_time_s, focus_points, corner_deltas}
    }


def validate_result(result: CoachResult, payload: dict[str, Any]) -> None:
    """Guard against advice that contradicts the data (anti-hallucination)."""
    corner_numbers = {c["corner"] for c in payload.get("corners", [])}
    # Generous ceiling: total observed loss plus a margin.
    ceiling = abs(payload.get("delta_to_reference_s") or 0.0) * 2 + 2.0

    if not result.summary_text:
        raise CoachValidationError("empty summary_text")
    for mistake in result.top_mistakes:
        corner = mistake.get("corner")
        if corner is not None and corner not in corner_numbers:
            raise CoachValidationError(f"mistake references unknown corner {corner}")
        loss = mistake.get("time_loss_s")
        if loss is not None and (loss < 0 or loss > ceiling):
            raise CoachValidationError(f"implausible time_loss_s={loss}")
    for fp in result.focus_points:
        corner = fp.get("corner")
        if corner is not None and corner not in corner_numbers:
            raise CoachValidationError(f"focus_point references unknown corner {corner}")
