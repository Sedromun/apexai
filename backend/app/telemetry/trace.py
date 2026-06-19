"""Canonical lap trace format (``lap-trace/1``) and (de)serialization.

A trace is **columnar**: equal-length arrays per channel. On the wire and in object
storage it is gzip-compressed JSON. Columnar + gzip keeps a ~90 s F1 lap (≈5 400 samples
× ~10 channels) at tens of KB, and the web charts (uPlot) consume the arrays directly.

This module is the contract shared by the desktop client (slice 2, which fills these
arrays from F1 UDP packets) and the backend. Keep it dependency-free and well-tested.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "lap-trace/1"

REQUIRED_CHANNELS: tuple[str, ...] = (
    "t_ms",  # milliseconds since lap start
    "lap_dist_m",  # distance along the lap, metres
    "speed_kmh",
    "throttle",  # 0..1
    "brake",  # 0..1
    "steer",  # -1..1 (left..right)
    "gear",  # integer
    "rpm",
)
OPTIONAL_CHANNELS: tuple[str, ...] = ("clutch", "drs", "pos_x", "pos_y", "pos_z")
ALL_CHANNELS: tuple[str, ...] = REQUIRED_CHANNELS + OPTIONAL_CHANNELS

# Guardrails against malformed / abusive payloads.
MAX_POINTS = 50_000  # a 60 Hz lap is ~5 400; even a long out-lap stays well under this.


class TraceValidationError(ValueError):
    """Raised when a trace payload is structurally invalid."""


@dataclass(slots=True)
class LapTrace:
    hz: int
    channels: dict[str, list[float]]
    schema_version: str = SCHEMA_VERSION

    @property
    def points(self) -> int:
        return len(self.channels.get("t_ms", []))

    def validate(self) -> None:
        if not self.schema_version.startswith("lap-trace/"):
            raise TraceValidationError(f"Unsupported schema: {self.schema_version!r}")
        if not isinstance(self.hz, int) or self.hz <= 0:
            raise TraceValidationError("hz must be a positive integer")

        missing = [c for c in REQUIRED_CHANNELS if c not in self.channels]
        if missing:
            raise TraceValidationError(f"Missing required channels: {', '.join(missing)}")

        unknown = [c for c in self.channels if c not in ALL_CHANNELS]
        if unknown:
            raise TraceValidationError(f"Unknown channels: {', '.join(unknown)}")

        n = self.points
        if n == 0:
            raise TraceValidationError("Trace is empty")
        if n > MAX_POINTS:
            raise TraceValidationError(f"Trace too long: {n} > {MAX_POINTS} points")

        for name, values in self.channels.items():
            if not isinstance(values, list):
                raise TraceValidationError(f"Channel {name!r} must be a list")
            if len(values) != n:
                raise TraceValidationError(
                    f"Channel {name!r} length {len(values)} != {n} (channels must align)"
                )
            if not all(isinstance(v, (int, float)) for v in values):
                raise TraceValidationError(f"Channel {name!r} has non-numeric values")

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema_version, "hz": self.hz, "channels": self.channels}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LapTrace:
        if not isinstance(data, dict):
            raise TraceValidationError("Trace must be a JSON object")
        channels = data.get("channels")
        if not isinstance(channels, dict):
            raise TraceValidationError("Trace 'channels' must be an object")
        trace = cls(
            hz=data.get("hz", 0),
            channels=channels,
            schema_version=data.get("schema", SCHEMA_VERSION),
        )
        trace.validate()
        return trace

    def to_gzip(self) -> bytes:
        raw = json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")
        return gzip.compress(raw, compresslevel=6)

    @classmethod
    def from_gzip(cls, blob: bytes) -> LapTrace:
        try:
            raw = gzip.decompress(blob)
        except (OSError, EOFError) as exc:
            raise TraceValidationError("Trace is not valid gzip data") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TraceValidationError("Trace is not valid JSON") from exc
        return cls.from_dict(data)
