#!/usr/bin/env python3
"""Generate a modeled 'ideal lap' reference trace per track from real circuit
geometry (bacinger/f1-circuits) using a quasi-steady-state lap simulation:

  curvature -> cornering-speed limit -> forward (accel) + backward (brake) passes
  -> speed-by-distance, then calibrate to the real lap record.

Output: backend/app/data/references/<slug>.json.gz in the lap-trace/1 contract,
plus references/index.json (meta). These are MODELED references, labeled as such.

    python tools/track_data/build_reference_laps.py
"""
import gzip
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
TRACKS = json.loads((ROOT / "backend" / "app" / "data" / "tracks.json").read_text())
GEO = {f["properties"]["id"]: f for f in json.loads(pathlib.Path("/tmp/f1-circuits.geojson").read_text())["features"]}
OUTDIR = ROOT / "backend" / "app" / "data" / "references"

A_LAT = 33.0   # m/s^2 lateral grip (~3.4g)
A_ACC = 13.0   # m/s^2 power/traction-limited acceleration (~1.3g)
A_BRAKE = 48.0  # m/s^2 braking (~4.9g)
V_MAX = 94.0   # m/s top speed (~338 km/h)
N = 600        # resample points


def smooth(arr, passes=1):
    """Circular 3-tap low-pass, applied `passes` times."""
    n = len(arr)
    a = list(arr)
    for _ in range(passes):
        a = [(a[(i - 1) % n] + 2 * a[i] + a[(i + 1) % n]) / 4 for i in range(n)]
    return a


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def record_seconds(record):
    if not record:
        return None
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)", record)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def local_xy(coords):
    lon0, lat0 = coords[0]
    kx = math.cos(math.radians(lat0)) * 111320.0
    ky = 111320.0
    return [((lon - lon0) * kx, (lat - lat0) * ky) for lon, lat in coords]


def resample(xy, length_m, n):
    """Evenly spaced points (closed loop) scaled to the official length."""
    # cumulative arc length of the raw polyline
    cum = [0.0]
    for i in range(1, len(xy)):
        cum.append(cum[-1] + math.dist(xy[i], xy[i - 1]))
    raw_total = cum[-1]
    s = length_m / raw_total  # scale geometry to real length
    step = length_m / n
    out = []
    j = 0
    for i in range(n):
        target = i * step / s  # in raw units
        while j < len(cum) - 2 and cum[j + 1] < target:
            j += 1
        seg = cum[j + 1] - cum[j] or 1e-9
        f = (target - cum[j]) / seg
        x = xy[j][0] + f * (xy[j + 1][0] - xy[j][0])
        y = xy[j][1] + f * (xy[j + 1][1] - xy[j][1])
        out.append((x * s, y * s))
    return out, step


def curvature(pts):
    n = len(pts)
    kappa = [0.0] * n
    sgn = [0.0] * n
    for i in range(n):
        a, b, c = pts[(i - 2) % n], pts[i], pts[(i + 2) % n]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        l1 = math.hypot(*v1) or 1e-9
        l2 = math.hypot(*v2) or 1e-9
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        ang = math.atan2(cross, dot)
        ds = (l1 + l2) / 2
        kappa[i] = abs(ang) / ds
        sgn[i] = -1.0 if cross < 0 else 1.0
    return smooth(kappa, 3), smooth(sgn, 1)


def gear_for(v_kmh):
    for g, top in enumerate([70, 110, 150, 195, 240, 290, 999], start=2):
        if v_kmh <= top:
            return g
    return 8


def build(name, info):
    gid = info["map"]["source_id"]
    pts, ds = resample(local_xy(GEO[gid]["geometry"]["coordinates"]), info["length_m"], N)
    kappa, sgn = curvature(pts)

    v = [min(V_MAX, math.sqrt(A_LAT / k)) if k > 1e-6 else V_MAX for k in kappa]
    for _ in range(2):  # forward (accel) then backward (brake), looped for the closed lap
        for i in range(1, N):
            v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * A_ACC * ds))
        v[0] = min(v[0], math.sqrt(v[-1] ** 2 + 2 * A_ACC * ds))
        for i in range(N - 2, -1, -1):
            v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * A_BRAKE * ds))
        v[-1] = min(v[-1], math.sqrt(v[0] ** 2 + 2 * A_BRAKE * ds))

    # smooth out centerline-vertex jitter, cap at top speed, then calibrate to
    # the lap record by scaling and re-capping.
    v = smooth(v, 3)
    v = [min(V_MAX, vi) for vi in v]
    t_model = sum(ds / vi for vi in v)
    rec = record_seconds(info["record"]) or t_model
    v = [min(V_MAX, vi * (t_model / rec)) for vi in v]

    t_ms, dist, speed, thr, brk, steer, gear, rpm = [], [], [], [], [], [], [], []
    t = 0.0
    kmax = max(kappa) or 1e-6
    for i in range(N):
        a_long = (v[(i + 1) % N] ** 2 - v[i] ** 2) / (2 * ds)
        # Ideal lap: full throttle everywhere except genuine braking zones
        # (deadzone avoids spurious micro-zones from tiny speed wiggles).
        if a_long < -2.0:
            thr_i, brk_i = 0.0, round(min(1.0, -a_long / A_BRAKE), 3)
        else:
            thr_i, brk_i = 1.0, 0.0
        t_ms.append(round(t * 1000))
        dist.append(round(i * ds, 1))
        speed.append(round(v[i] * 3.6, 1))
        thr.append(thr_i)
        brk.append(brk_i)
        steer.append(round(max(-1.0, min(1.0, sgn[i] * kappa[i] / kmax)), 3))
        gear.append(gear_for(v[i] * 3.6))
        rpm.append(round(7000 + 4500 * min(1.0, (v[i] * 3.6 % 60) / 60)))
        t += ds / v[i]

    trace = {
        "schema": "lap-trace/1",
        "hz": round(N / t),
        "channels": {
            "t_ms": t_ms, "lap_dist_m": dist, "speed_kmh": speed, "throttle": thr,
            "brake": brk, "steer": steer, "gear": gear, "rpm": rpm,
        },
    }
    return trace, t


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, info in TRACKS.items():
        if not info.get("map"):
            continue
        trace, t = build(name, info)
        sl = slug(name)
        (OUTDIR / f"{sl}.json.gz").write_bytes(gzip.compress(json.dumps(trace).encode()))
        index[name] = {
            "slug": sl, "lap_time_ms": round(t * 1000), "kind": "modeled",
            "label": "Идеальный круг (модель)", "samples": len(trace["channels"]["t_ms"]),
            "max_speed_kmh": max(trace["channels"]["speed_kmh"]),
        }
    (OUTDIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(f"wrote {len(index)} reference laps -> {OUTDIR}")
    for k in ("Zandvoort", "Monza", "Spa"):
        e = index[k]
        mm, ss = divmod(e["lap_time_ms"] / 1000, 60)
        print(f"  {k:20} {int(mm)}:{ss:06.3f}  vmax={e['max_speed_kmh']}km/h  ({e['samples']} pts)")


if __name__ == "__main__":
    main()
