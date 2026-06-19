"""Track catalog: metadata, circuit maps, and the modeled reference laps."""
from app.services import track_catalog
from app.telemetry.trace import LapTrace


def test_zandvoort_metadata_has_all_corners_and_map():
    t = track_catalog.get_track("Zandvoort")
    assert t is not None
    assert t["corner_count"] == 14
    assert len(t["corners"]) == 14
    assert t["corners"][0] == {"n": 1, "name": "Tarzanbocht"}
    assert t["corners"][-1]["name"] == "Arie Luyendyk Bocht"
    assert t["map"] and t["map"]["path"].startswith("M")
    assert t["map"]["view_box"] == "0 0 1000 1000"


def test_every_reference_trace_is_valid_and_calibrated():
    named = [n for n in track_catalog.list_tracks() if track_catalog.reference_meta(n)]
    assert len(named) >= 28
    for name in named:
        trace = track_catalog.reference_trace(name)
        assert isinstance(trace, LapTrace)
        trace.validate()  # raises on a malformed/short trace
        meta = track_catalog.reference_meta(name)
        assert meta["kind"] == "modeled"
        assert meta["lap_time_ms"] > 10_000
        assert trace.channels["lap_dist_m"][-1] > 1000
        assert max(trace.channels["speed_kmh"]) < 400


def test_reference_trace_is_cached():
    a = track_catalog.reference_trace("Monza")
    b = track_catalog.reference_trace("Monza")
    assert a is b  # second call returns the cached instance


def test_unknown_track_returns_none():
    assert track_catalog.get_track("Nope") is None
    assert track_catalog.reference_meta("Nope") is None
    assert track_catalog.reference_trace("Nope") is None
