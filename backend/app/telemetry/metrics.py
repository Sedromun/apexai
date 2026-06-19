"""Layer-1 deterministic lap analysis.

Pure math over a :class:`LapTrace`: segment the lap into corners and compute per-corner
and overall metrics. The output is the compact "lap-metrics/1" JSON that drives the free
charts and, later, feeds the (paid) LLM coach. No AI here — just numbers.

Dependency-free and fully deterministic so it is cheap and unit-testable.
"""

from __future__ import annotations

import bisect
from typing import Any

from app.telemetry.trace import LapTrace

METRICS_SCHEMA = "lap-metrics/1"

# Tuning constants for corner detection.
_SMOOTH_WINDOW = 13  # samples (~0.2 s @ 60 Hz)
_CORNER_SPEED_FRACTION = 0.90  # speed below this fraction of lap max => inside a corner
_ENTRY_EXIT_LOOKAROUND_M = 300.0  # search window for entry/exit speed maxima
_MERGE_GAP_M = 180.0  # merge apexes closer than this
_BRAKE_ON = 0.10
_THROTTLE_FULL = 0.90
_STEER_ENGAGED = 0.10
_REVERSAL_DEADBAND = 0.01


def _moving_average(values: list[float], window: int) -> list[float]:
    n = len(values)
    if window <= 1 or n == 0:
        return list(values)
    prefix = [0.0] * (n + 1)
    for i, v in enumerate(values):
        prefix[i + 1] = prefix[i] + v
    half = window // 2
    out = [0.0] * n
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        out[i] = (prefix[hi] - prefix[lo]) / (hi - lo)
    return out


def _count_reversals(steer: list[float], lo: int, hi: int) -> int:
    """Number of steering-direction changes in [lo, hi] (a smoothness proxy)."""
    prev_sign = 0
    count = 0
    for k in range(lo, hi):
        delta = steer[k + 1] - steer[k]
        if abs(delta) < _REVERSAL_DEADBAND:
            continue
        sign = 1 if delta > 0 else -1
        if prev_sign != 0 and sign != prev_sign:
            count += 1
        prev_sign = sign
    return count


def segment_corners(trace: LapTrace) -> list[dict[str, Any]]:
    """Detect corners as contiguous regions where (smoothed) speed dips below a fraction
    of the lap's maximum. For each, find entry/apex/exit and per-corner metrics."""
    ch = trace.channels
    speed = ch["speed_kmh"]
    dist = ch["lap_dist_m"]
    steer = ch["steer"]
    brake = ch["brake"]
    throttle = ch["throttle"]
    t_ms = ch["t_ms"]
    n = len(speed)
    if n < 10:
        return []

    smooth = _moving_average(speed, _SMOOTH_WINDOW)
    threshold = max(smooth) * _CORNER_SPEED_FRACTION

    # Contiguous below-threshold regions => corner zones.
    regions: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if smooth[i] < threshold:
            j = i
            while j < n and smooth[j] < threshold:
                j += 1
            regions.append((i, j - 1))
            i = j
        else:
            i += 1

    corners: list[dict[str, Any]] = []
    for start, end in regions:
        apex = min(range(start, end + 1), key=lambda k: speed[k])
        apex_d = dist[apex]

        lo = max(0, min(bisect.bisect_left(dist, apex_d - _ENTRY_EXIT_LOOKAROUND_M), apex))
        hi = min(n - 1, max(bisect.bisect_right(dist, apex_d + _ENTRY_EXIT_LOOKAROUND_M) - 1, apex))
        entry = max(range(lo, apex + 1), key=lambda k: speed[k])
        exit_ = max(range(apex, hi + 1), key=lambda k: speed[k])

        brake_point = next((k for k in range(entry, apex + 1) if brake[k] > _BRAKE_ON), entry)
        throttle_point = next(
            (k for k in range(apex, exit_ + 1) if throttle[k] > _THROTTLE_FULL), exit_
        )

        trail_brake_m = 0.0
        for k in range(entry, exit_):
            if brake[k] > 0.05 and abs(steer[k]) > _STEER_ENGAGED:
                trail_brake_m += dist[k + 1] - dist[k]

        peak_brake = max(brake[entry : apex + 1], default=0.0)
        direction = "right" if sum(steer[start : end + 1]) >= 0 else "left"

        corners.append(
            {
                "entry_dist_m": round(dist[entry], 1),
                "apex_dist_m": round(apex_d, 1),
                "exit_dist_m": round(dist[exit_], 1),
                "entry_speed_kmh": round(speed[entry], 1),
                "apex_speed_kmh": round(speed[apex], 1),
                "exit_speed_kmh": round(speed[exit_], 1),
                "brake_point_dist_m": round(dist[brake_point], 1),
                "brake_to_apex_m": round(apex_d - dist[brake_point], 1),
                "peak_brake": round(peak_brake, 3),
                "throttle_point_dist_m": round(dist[throttle_point], 1),
                "trail_brake_overlap_m": round(trail_brake_m, 1),
                "steering_reversals": _count_reversals(steer, entry, exit_),
                "direction": direction,
                "time_s": round((t_ms[exit_] - t_ms[entry]) / 1000.0, 3),
            }
        )

    corners = _merge_close_corners(corners)
    for number, corner in enumerate(corners, start=1):
        corner["number"] = number
    return corners


def _merge_close_corners(corners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not corners:
        return corners
    corners = sorted(corners, key=lambda c: c["apex_dist_m"])
    merged = [corners[0]]
    for corner in corners[1:]:
        if corner["apex_dist_m"] - merged[-1]["apex_dist_m"] < _MERGE_GAP_M:
            # Keep the tighter corner (lower apex speed).
            if corner["apex_speed_kmh"] < merged[-1]["apex_speed_kmh"]:
                merged[-1] = corner
        else:
            merged.append(corner)
    return merged


def compute_lap_metrics(trace: LapTrace) -> dict[str, Any]:
    """Full layer-1 metrics for one lap (the compact JSON stored on the lap row)."""
    ch = trace.channels
    n = trace.points
    speed = ch["speed_kmh"]
    throttle = ch["throttle"]
    brake = ch["brake"]
    steer = ch["steer"]
    dist = ch["lap_dist_m"]
    t_ms = ch["t_ms"]

    corners = segment_corners(trace)

    full_throttle = sum(1 for v in throttle if v > 0.95)
    braking = sum(1 for v in brake if v > 0.05)
    trail = sum(1 for k in range(n) if brake[k] > 0.05 and abs(steer[k]) > _STEER_ENGAGED)
    apex_speeds = [c["apex_speed_kmh"] for c in corners]

    return {
        "schema": METRICS_SCHEMA,
        "lap_time_ms": int(round(t_ms[-1])),
        "summary": {
            "distance_m": round(dist[-1], 1),
            "top_speed_kmh": round(max(speed), 1),
            "min_speed_kmh": round(min(speed), 1),
            "avg_speed_kmh": round(sum(speed) / n, 1),
            "full_throttle_pct": round(100.0 * full_throttle / n, 1),
            "braking_pct": round(100.0 * braking / n, 1),
            "trail_braking_pct": round(100.0 * trail / n, 1),
            "corner_count": len(corners),
            "avg_apex_speed_kmh": round(sum(apex_speeds) / len(apex_speeds), 1)
            if apex_speeds
            else None,
            "steering_reversals_total": sum(c["steering_reversals"] for c in corners),
        },
        "corners": corners,
    }
