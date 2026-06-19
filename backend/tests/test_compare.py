from app.telemetry.compare import compute_delta
from app.telemetry.synth import SIM_CIRCUIT, generate_lap, lap_time_ms


def test_delta_against_self_is_zero():
    trace = generate_lap(SIM_CIRCUIT.name, seed=0)
    delta = compute_delta(trace, trace)
    assert abs(delta["total_delta_s"]) < 1e-6
    assert max(abs(x) for x in delta["delta_s"]) < 0.01
    assert len(delta["distance_m"]) == len(delta["delta_s"])


def test_slower_lap_has_positive_total_delta():
    fast = generate_lap(SIM_CIRCUIT.name, seed=0)
    slow = generate_lap(SIM_CIRCUIT.name, seed=2)
    delta = compute_delta(slow, fast)  # self = slow, reference = fast

    expected = (lap_time_ms(slow) - lap_time_ms(fast)) / 1000.0
    assert delta["total_delta_s"] > 0
    assert abs(delta["total_delta_s"] - expected) < 0.05
    # losing time across the lap: final cumulative delta >= initial
    assert delta["delta_s"][-1] >= delta["delta_s"][0]


def test_delta_distance_grid_is_monotonic():
    delta = compute_delta(generate_lap(seed=0), generate_lap(seed=1))
    grid = delta["distance_m"]
    assert all(grid[i] < grid[i + 1] for i in range(len(grid) - 1))
    assert grid[0] == 0.0
