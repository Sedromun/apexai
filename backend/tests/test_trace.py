import pytest

from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms
from app.telemetry.trace import REQUIRED_CHANNELS, LapTrace, TraceValidationError


def _channels(n: int = 3) -> dict[str, list[float]]:
    return {name: [0.0] * n for name in REQUIRED_CHANNELS}


def test_gzip_roundtrip_preserves_data():
    trace = LapTrace(hz=60, channels=_channels(5))
    restored = LapTrace.from_gzip(trace.to_gzip())
    assert restored.hz == 60
    assert restored.points == 5
    assert restored.channels == trace.channels


def test_missing_required_channel_rejected():
    channels = _channels()
    del channels["throttle"]
    with pytest.raises(TraceValidationError):
        LapTrace(hz=60, channels=channels).validate()


def test_misaligned_channels_rejected():
    channels = _channels(4)
    channels["brake"] = [0.0] * 3
    with pytest.raises(TraceValidationError):
        LapTrace(hz=60, channels=channels).validate()


def test_unknown_channel_rejected():
    channels = _channels()
    channels["boost"] = [1.0] * 3
    with pytest.raises(TraceValidationError):
        LapTrace(hz=60, channels=channels).validate()


def test_non_positive_hz_rejected():
    with pytest.raises(TraceValidationError):
        LapTrace(hz=0, channels=_channels()).validate()


def test_from_gzip_rejects_non_gzip():
    with pytest.raises(TraceValidationError):
        LapTrace.from_gzip(b"definitely not gzip")


def test_synthetic_lap_is_valid_and_plausible():
    trace = generate_lap(SIM_CIRCUIT.name, seed=0)
    trace.validate()  # must not raise

    n = trace.points
    assert n > 1000  # ~90 s @ 60 Hz
    assert all(len(values) == n for values in trace.channels.values())

    assert all(0.0 <= v <= 1.0 for v in trace.channels["throttle"])
    assert all(0.0 <= v <= 1.0 for v in trace.channels["brake"])
    assert all(-1.0 <= v <= 1.0 for v in trace.channels["steer"])
    assert 0.0 < min(trace.channels["speed_kmh"])
    assert max(trace.channels["speed_kmh"]) <= 330.0

    distance = trace.channels["lap_dist_m"]
    assert all(distance[i] <= distance[i + 1] + 1e-6 for i in range(n - 1))


def test_reference_lap_is_fastest():
    reference = lap_time_ms(generate_lap(seed=0))
    assert reference <= lap_time_ms(generate_lap(seed=1))
    assert reference <= lap_time_ms(generate_lap(seed=2))
