from app.telemetry.metrics import compute_lap_metrics, segment_corners
from app.telemetry.synth import SIM_CIRCUIT, generate_lap


def test_segments_multiple_corners():
    corners = segment_corners(generate_lap(SIM_CIRCUIT.name, seed=0))
    assert len(corners) >= 5
    for c in corners:
        # apex is the slowest point of the corner
        assert c["apex_speed_kmh"] <= c["entry_speed_kmh"]
        assert c["apex_speed_kmh"] <= c["exit_speed_kmh"]
        # ordering: entry -> brake point -> apex -> exit (by distance)
        assert c["entry_dist_m"] <= c["apex_dist_m"] <= c["exit_dist_m"]
        assert c["brake_point_dist_m"] <= c["apex_dist_m"]
        assert c["direction"] in ("left", "right")
        assert c["number"] >= 1


def test_lap_metrics_summary_is_sane():
    metrics = compute_lap_metrics(generate_lap(SIM_CIRCUIT.name, seed=0))
    assert metrics["schema"] == "lap-metrics/1"

    summary = metrics["summary"]
    assert 250 <= summary["top_speed_kmh"] <= 330
    assert 0 <= summary["full_throttle_pct"] <= 100
    assert 0 <= summary["braking_pct"] <= 100
    assert summary["corner_count"] == len(metrics["corners"])
    assert summary["corner_count"] >= 5
    assert summary["min_speed_kmh"] <= summary["avg_speed_kmh"] <= summary["top_speed_kmh"]


def test_corner_numbers_are_sequential():
    corners = segment_corners(generate_lap(SIM_CIRCUIT.name, seed=0))
    assert [c["number"] for c in corners] == list(range(1, len(corners) + 1))
    # apex distances strictly increasing along the lap
    apexes = [c["apex_dist_m"] for c in corners]
    assert all(apexes[i] < apexes[i + 1] for i in range(len(apexes) - 1))
