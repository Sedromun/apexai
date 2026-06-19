#!/usr/bin/env python3
"""Convert a Racenet 'performanceAnalysis/ghost' lap (extracted from the chart
props in the browser) into a lap-trace/1 reference and register it in
backend/app/data/references/index.json as a REAL reference lap.

Raw input format (tools/track_data/racenet/<slug>.json), all arrays len N:
  { track, driver, rank, laptime_ms, vehicle, assists,
    dist_dm[], t_ms[], speed_dkmh[], thr[], brk[], gear[], steer_pct10[] }

    python tools/track_data/racenet_to_reference.py tools/track_data/racenet/zandvoort.json "Zandvoort"
"""
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REFDIR = ROOT / "backend" / "app" / "data" / "references"

# Approx top speed (km/h) per gear — gives a plausible rpm sawtooth (Racenet has no rpm channel).
GEAR_TOP = {1: 80, 2: 120, 3: 160, 4: 200, 5: 240, 6: 280, 7: 312, 8: 335}
REDLINE = 13000


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def rpm_for(speed_kmh, gear):
    if gear < 1:
        return 5000
    return int(min(REDLINE, max(5000, speed_kmh / GEAR_TOP.get(gear, 335) * REDLINE)))


def main(raw_path, track):
    raw = json.loads(pathlib.Path(raw_path).read_text())
    n = len(raw["dist_dm"])
    speed = [s / 10 for s in raw["speed_dkmh"]]
    gear = [max(0, min(8, g)) for g in raw["gear"]]
    trace = {
        "schema": "lap-trace/1",
        "hz": max(1, round(n / (raw["laptime_ms"] / 1000))),
        "channels": {
            "t_ms": [int(t) for t in raw["t_ms"]],
            "lap_dist_m": [round(d / 10, 1) for d in raw["dist_dm"]],
            "speed_kmh": [round(s, 1) for s in speed],
            "throttle": [round(t / 100, 3) for t in raw["thr"]],
            "brake": [round(b / 100, 3) for b in raw["brk"]],
            "steer": [round(max(-1.0, min(1.0, s / 1000)), 3) for s in raw["steer_pct10"]],
            "gear": gear,
            "rpm": [rpm_for(speed[i], gear[i]) for i in range(n)],
        },
    }
    # sanity: aligned, monotonic distance/time
    assert all(len(v) == n for v in trace["channels"].values())

    sl = slug(track)
    (REFDIR / f"{sl}.json.gz").write_bytes(gzip.compress(json.dumps(trace).encode()))

    index = json.loads((REFDIR / "index.json").read_text())
    index[track] = {
        "slug": sl,
        "lap_time_ms": int(raw["laptime_ms"]),
        "kind": "real",
        "label": f"Реальный круг — {raw['driver']} (F1 25)",
        "driver": raw["driver"],
        "source": "racenet",
        "samples": n,
        "max_speed_kmh": round(max(speed), 1),
    }
    (REFDIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    mm, ss = divmod(raw["laptime_ms"] / 1000, 60)
    print(f"{track}: real reference from {raw['driver']} {int(mm)}:{ss:06.3f} "
          f"({n} pts, vmax {round(max(speed),1)} km/h) -> {sl}.json.gz")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
