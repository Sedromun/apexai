"""Static per-track catalog: corner lists, circuit-map geometry, and the modeled
'ideal lap' reference traces.

The data is generated offline (see tools/track_data/) and shipped as JSON +
gzipped traces under ``app/data``. This module loads it once at import and caches
decoded reference traces lazily. No database — it's read-only reference data.
"""
from __future__ import annotations

import json
import pathlib
import threading
from typing import Any

from app.telemetry.trace import LapTrace

_DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
_TRACKS: dict[str, Any] = json.loads((_DATA / "tracks.json").read_text(encoding="utf-8"))
_REF_INDEX: dict[str, Any] = json.loads(
    (_DATA / "references" / "index.json").read_text(encoding="utf-8")
)

_ref_cache: dict[str, LapTrace] = {}
_lock = threading.Lock()


def get_track(name: str) -> dict[str, Any] | None:
    """Track metadata (length, corners, map, record) or None if unknown."""
    return _TRACKS.get(name)


def reference_meta(name: str) -> dict[str, Any] | None:
    """Metadata for the modeled reference lap (label, lap_time_ms, kind) or None."""
    return _REF_INDEX.get(name)


def reference_trace(name: str) -> LapTrace | None:
    """The modeled reference lap trace for a track (cached), or None if none exists."""
    meta = _REF_INDEX.get(name)
    if meta is None:
        return None
    slug = meta["slug"]
    with _lock:
        cached = _ref_cache.get(slug)
        if cached is None:
            blob = (_DATA / "references" / f"{slug}.json.gz").read_bytes()
            cached = LapTrace.from_gzip(blob)
            _ref_cache[slug] = cached
        return cached


def list_tracks() -> list[str]:
    return list(_TRACKS.keys())
