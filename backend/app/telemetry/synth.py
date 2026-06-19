"""Deterministic synthetic F1 lap generator.

Used to seed demo data and to exercise the charts before the desktop client exists.
It is a physics-*lite* simulation: a speed target is derived from a track layout, then
integrated forward in time with bounded acceleration/braking, and the remaining channels
(throttle, brake, steer, gear, rpm) are derived from that motion. The goal is telemetry
that *looks* and *segments* like a real lap — not a faithful vehicle model.

``seed=0`` is the fastest (reference) lap; higher seeds are slightly slower, which gives
the comparison/delta features (slice 3) something real to chew on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.telemetry.trace import LapTrace


@dataclass(frozen=True)
class Corner:
    center_m: float
    apex_kmh: float
    direction: int  # -1 left, +1 right
    influence_m: float  # half-width of the corner's effect on the speed target


@dataclass(frozen=True)
class TrackLayout:
    name: str
    length_m: float
    top_speed_kmh: float
    corners: tuple[Corner, ...]


SIM_CIRCUIT = TrackLayout(
    name="Sim Circuit",
    length_m=5200.0,
    top_speed_kmh=315.0,
    corners=(
        Corner(620, 118, +1, 150),
        Corner(1260, 86, -1, 130),
        Corner(1980, 205, +1, 110),
        Corner(2600, 95, -1, 140),
        Corner(3250, 142, +1, 120),
        Corner(3820, 70, -1, 160),
        Corner(4500, 165, +1, 120),
        Corner(4980, 110, -1, 110),
    ),
)

TRACKS: dict[str, TrackLayout] = {SIM_CIRCUIT.name: SIM_CIRCUIT}

_GEAR_MAX_KMH = (60.0, 100.0, 142.0, 186.0, 228.0, 268.0, 300.0, 1e9)  # upper bound per gear 1..8


class _Lcg:
    """Tiny deterministic PRNG so a given seed always yields the same lap (no Math.random)."""

    def __init__(self, seed: int) -> None:
        self._state = (seed * 2_654_435_761 + 12345) & 0xFFFFFFFF

    def uniform(self, lo: float, hi: float) -> float:
        self._state = (1_103_515_245 * self._state + 12345) & 0x7FFFFFFF
        return lo + (self._state / 0x7FFFFFFF) * (hi - lo)


def _gear_for_speed(speed_kmh: float) -> int:
    for gear, upper in enumerate(_GEAR_MAX_KMH, start=1):
        if speed_kmh <= upper:
            return gear
    return 8


def _rpm_for(speed_kmh: float, gear: int) -> float:
    lower = 0.0 if gear == 1 else _GEAR_MAX_KMH[gear - 2]
    upper = _GEAR_MAX_KMH[gear - 1]
    span = max(upper - lower, 1.0)
    frac = min(max((speed_kmh - lower) / span, 0.0), 1.0)
    return round(9500.0 + frac * 2500.0, 1)


def _target_speed_kmh(dist_m: float, layout: TrackLayout, slowdown: float) -> float:
    speed = layout.top_speed_kmh
    for corner in layout.corners:
        d = abs(dist_m - corner.center_m)
        if d < corner.influence_m:
            frac = d / corner.influence_m
            apex = corner.apex_kmh * slowdown
            cornered = apex + (layout.top_speed_kmh - apex) * (frac**1.7)
            speed = min(speed, cornered)
    return speed


def _steer_at(dist_m: float, layout: TrackLayout) -> float:
    steer = 0.0
    for corner in layout.corners:
        d = abs(dist_m - corner.center_m)
        if d < corner.influence_m:
            weight = (1.0 - d / corner.influence_m) ** 1.3
            steer += corner.direction * weight
    return max(-1.0, min(1.0, steer))


def generate_lap(track: str = SIM_CIRCUIT.name, *, seed: int = 0, hz: int = 60) -> LapTrace:
    """Generate one deterministic synthetic lap as a validated :class:`LapTrace`."""
    layout = TRACKS.get(track)
    if layout is None:
        raise ValueError(f"Unknown track: {track!r}")

    rng = _Lcg(seed)
    # seed 0 = reference; later seeds brake a touch early and carry slightly less apex speed.
    slowdown = 1.0 if seed == 0 else rng.uniform(0.965, 0.995)

    dt = 1.0 / hz
    accel_ms2 = 14.0  # combined drive+aero longitudinal accel (m/s^2), lap-average-ish
    brake_ms2 = 32.0  # heavy braking deceleration (m/s^2)

    t_ms: list[float] = []
    lap_dist: list[float] = []
    speed_ch: list[float] = []
    throttle_ch: list[float] = []
    brake_ch: list[float] = []
    steer_ch: list[float] = []
    gear_ch: list[float] = []
    rpm_ch: list[float] = []

    dist = 0.0
    elapsed = 0.0
    v = layout.top_speed_kmh / 3.6 * 0.97  # flying lap: start near top speed
    max_steps = hz * 240  # safety bound (240 s)

    for _ in range(max_steps):
        if dist >= layout.length_m:
            break
        target = _target_speed_kmh(dist, layout, slowdown) / 3.6

        if v < target:
            v = min(target, v + accel_ms2 * dt)
            throttle = 1.0
            brake = 0.0
        else:
            decel_needed = (v - target) / dt
            applied = min(decel_needed, brake_ms2)
            v = max(target, v - applied * dt)
            brake = min(1.0, applied / brake_ms2)
            # light trail-braking feel: ease off throttle fully under braking
            throttle = 0.0 if brake > 0.05 else 1.0

        steer = _steer_at(dist, layout)
        speed_kmh = v * 3.6
        gear = _gear_for_speed(speed_kmh)

        t_ms.append(round(elapsed * 1000.0, 1))
        lap_dist.append(round(dist, 2))
        speed_ch.append(round(speed_kmh, 2))
        throttle_ch.append(round(throttle, 3))
        brake_ch.append(round(brake, 3))
        steer_ch.append(round(steer, 3))
        gear_ch.append(gear)
        rpm_ch.append(_rpm_for(speed_kmh, gear))

        dist += v * dt
        elapsed += dt

    trace = LapTrace(
        hz=hz,
        channels={
            "t_ms": t_ms,
            "lap_dist_m": lap_dist,
            "speed_kmh": speed_ch,
            "throttle": throttle_ch,
            "brake": brake_ch,
            "steer": steer_ch,
            "gear": gear_ch,
            "rpm": rpm_ch,
        },
    )
    trace.validate()
    return trace


def lap_time_ms(trace: LapTrace) -> int:
    return int(round(trace.channels["t_ms"][-1])) if trace.points else 0
