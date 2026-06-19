"""Corner detector: prominence-based local minima must find every braking corner
(regression guard for the 'Zandvoort shows only 3 corners' bug)."""
import math

from app.telemetry.metrics import segment_corners
from app.telemetry.trace import LapTrace


def _synthetic_lap(n_corners: int) -> LapTrace:
    """A lap with `n_corners` distinct speed dips (≈100 km/h) on a ~300 km/h base."""
    n = 2000
    dist = [i * 3.0 for i in range(n)]
    t_ms = [i * 50 for i in range(n)]
    speed = []
    for i in range(n):
        frac = i / n
        v = 300.0
        for k in range(n_corners):
            center = (k + 0.5) / n_corners
            v -= 200.0 * math.exp(-((abs(frac - center) * n_corners * 3) ** 2))
        speed.append(max(80.0, v))
    z = [0.0] * n
    return LapTrace(
        hz=20,
        channels={
            "t_ms": t_ms, "lap_dist_m": dist, "speed_kmh": speed,
            "throttle": z, "brake": z, "steer": z, "gear": [4] * n, "rpm": [9000.0] * n,
        },
    )


def test_detector_finds_all_distinct_corners():
    corners = segment_corners(_synthetic_lap(6))
    # The old global-threshold detector collapsed twisty laps to 1-3 regions; the
    # prominence detector must find each dip.
    assert 5 <= len(corners) <= 7
    # numbered in order along the lap
    assert [c["number"] for c in corners] == list(range(1, len(corners) + 1))
    apexes = [c["apex_dist_m"] for c in corners]
    assert apexes == sorted(apexes)


def test_detector_ignores_flat_lap():
    # No real dips → no corners (tiny wiggles must not register).
    n = 500
    flat = LapTrace(
        hz=20,
        channels={
            "t_ms": [i * 50 for i in range(n)], "lap_dist_m": [i * 3.0 for i in range(n)],
            "speed_kmh": [280.0 + (i % 3) for i in range(n)], "throttle": [1.0] * n,
            "brake": [0.0] * n, "steer": [0.0] * n, "gear": [7] * n, "rpm": [11000.0] * n,
        },
    )
    assert segment_corners(flat) == []
