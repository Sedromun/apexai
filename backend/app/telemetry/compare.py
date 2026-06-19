"""Lap-to-lap comparison: delta-time by distance + per-corner deltas.

The delta-time curve answers "where, and how much, am I gaining/losing vs the reference?".
At each distance ``d`` it is ``t_self(d) - t_ref(d)`` in seconds: positive => self is behind.
The value at the end of the lap equals the lap-time difference.
"""

from __future__ import annotations

import bisect
from typing import Any

from app.telemetry.metrics import segment_corners
from app.telemetry.trace import LapTrace

_GRID_STEP_M = 5.0


def _time_at_distance(dist: list[float], t_ms: list[float], target: float) -> float:
    """Linear-interpolate elapsed time (ms) at a given lap distance."""
    if target <= dist[0]:
        return t_ms[0]
    if target >= dist[-1]:
        return t_ms[-1]
    i = bisect.bisect_left(dist, target)
    d0, d1 = dist[i - 1], dist[i]
    if d1 == d0:
        return t_ms[i]
    frac = (target - d0) / (d1 - d0)
    return t_ms[i - 1] + frac * (t_ms[i] - t_ms[i - 1])


def compute_delta(self_trace: LapTrace, ref_trace: LapTrace, step_m: float = _GRID_STEP_M) -> dict[str, Any]:
    self_dist = self_trace.channels["lap_dist_m"]
    self_t = self_trace.channels["t_ms"]
    ref_dist = ref_trace.channels["lap_dist_m"]
    ref_t = ref_trace.channels["t_ms"]

    max_d = min(self_dist[-1], ref_dist[-1])
    grid: list[float] = []
    d = 0.0
    while d <= max_d:
        grid.append(round(d, 1))
        d += step_m

    delta_s = [
        round((_time_at_distance(self_dist, self_t, g) - _time_at_distance(ref_dist, ref_t, g)) / 1000.0, 4)
        for g in grid
    ]

    corners = []
    for corner in segment_corners(self_trace):
        entry_d = corner["entry_dist_m"]
        exit_d = corner["exit_dist_m"]
        if exit_d > max_d:
            continue
        delta_in = (
            _time_at_distance(self_dist, self_t, entry_d)
            - _time_at_distance(ref_dist, ref_t, entry_d)
        ) / 1000.0
        delta_out = (
            _time_at_distance(self_dist, self_t, exit_d)
            - _time_at_distance(ref_dist, ref_t, exit_d)
        ) / 1000.0
        corners.append(
            {
                "number": corner["number"],
                "apex_dist_m": corner["apex_dist_m"],
                "delta_s": round(delta_out - delta_in, 3),
                "self_apex_kmh": corner["apex_speed_kmh"],
            }
        )

    return {
        "distance_m": grid,
        "delta_s": delta_s,
        "total_delta_s": round((self_t[-1] - ref_t[-1]) / 1000.0, 3),
        "corners": corners,
    }
