#!/usr/bin/env python3
"""Align each circuit's SVG outline to real driving distance so the hover marker
(track-map dot) tracks the car correctly — WITHOUT any racing-line position data.

The bacinger outline is a faithful track *shape*, but its arc-length doesn't
accumulate at the same rate as the lap distance the game reports, so a naive
distance→path-fraction mapping makes the dot lurch. We fix it by matching the
outline's own corners (curvature peaks) to the reference lap's corners (speed
minima) and storing a monotonic warp [[lapFrac, outlineFrac], ...]. The web then
maps a hover distance through this warp before sampling the path, so corners line
up exactly. Falls back to identity (no warp) when the match is poor, so a track is
never made worse.

    python tools/track_data/build_track_align.py   # rewrites tracks.json in place
"""
import gzip
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TRACKS = ROOT / "backend" / "app" / "data" / "tracks.json"
REFDIR = ROOT / "backend" / "app" / "data" / "references"
GEOJSON = pathlib.Path("/tmp/f1-circuits.geojson")


def outline_corners(coords):
    """(corner fractions, total turning) along the outline by arc length."""
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    mlat = sum(la for _, la in coords) / len(coords)
    kx = math.cos(math.radians(mlat))
    p = [(lo * kx, la) for lo, la in coords]
    n = len(p)
    seg = [math.dist(p[i], p[(i + 1) % n]) for i in range(n)]
    total = sum(seg)
    cum = [0.0] * n
    for i in range(1, n):
        cum[i] = cum[i - 1] + seg[i - 1]

    def turn(i):
        a, b, c = p[(i - 1) % n], p[i], p[(i + 1) % n]
        d = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0])
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        return abs(d)

    N = 400
    bins = [0.0] * N
    for i in range(n):
        bins[int(cum[i] / total * N) % N] += turn(i)
    sm = [sum(bins[(j + k) % N] for k in range(-4, 5)) / 9 for j in range(N)]
    mean = sum(sm) / N
    peaks = []
    for j in range(N):
        if sm[j] > mean * 1.3 and sm[j] == max(sm[(j + k) % N] for k in range(-8, 9)):
            if not peaks or (j - peaks[-1]) > 12:
                peaks.append(j)
    return [j / N for j in peaks]


def lap_corners(slug):
    """Reference-lap corner fractions = local speed minima."""
    path = REFDIR / f"{slug}.json.gz"
    if not path.exists():
        return None
    tr = json.loads(gzip.decompress(path.read_bytes()))
    d = tr["channels"]["lap_dist_m"]
    v = tr["channels"]["speed_kmh"]
    d0, dn = d[0], d[-1]
    vmax = max(v)
    w = 6
    mins = []
    for i in range(w, len(v) - w):
        if v[i] == min(v[i - w : i + w + 1]) and v[i] < vmax * 0.85:
            f = (d[i] - d0) / (dn - d0)
            if not mins or f - mins[-1] > 0.03:
                mins.append(f)
    return mins


def match(lap, out):
    """Greedy monotonic nearest match lap[i] -> outline corner; returns pairs + mean err."""
    pairs = []
    j = 0
    used = -1
    for lf in lap:
        best, berr = None, 1e9
        for k in range(used + 1, len(out)):
            e = abs(out[k] - lf)
            if e < berr:
                best, berr = k, e
        if best is None:
            continue
        used = best
        pairs.append((lf, out[best]))
    err = sum(abs(a - b) for a, b in pairs) / len(pairs) if pairs else 1.0
    return pairs, err


def build_warp(pairs):
    """Monotonic control points (0,0)..(1,1); drop any that break monotonicity."""
    cps = [(0.0, 0.0)]
    for lf, of in pairs:
        if lf > cps[-1][0] + 1e-3 and of > cps[-1][1] + 1e-3 and lf < 0.99 and of < 0.99:
            cps.append((round(lf, 4), round(of, 4)))
    cps.append((1.0, 1.0))
    return cps


def main():
    tracks = json.loads(TRACKS.read_text())
    geo = {f["properties"]["id"]: f for f in json.loads(GEOJSON.read_text())["features"]}
    warped = identity = 0
    for name, t in tracks.items():
        m = t.get("map")
        if not m:
            continue
        gid = m.get("source_id")
        ref = (t.get("reference") or {})
        slug = ref.get("slug") or name.lower().replace(" ", "-")
        lap = lap_corners(slug)
        if not gid or gid not in geo or not lap or len(lap) < 3:
            m["align_warp"] = None
            identity += 1
            continue
        out = outline_corners(geo[gid]["geometry"]["coordinates"])
        pairs, err = match(lap, out)
        if err < 0.05 and len(pairs) >= max(3, len(lap) - 2):
            m["align_warp"] = build_warp(pairs)
            warped += 1
            tag = f"warp ({len(pairs)} corners, err {err:.3f})"
        else:
            m["align_warp"] = None
            identity += 1
            tag = f"identity (err {err:.3f}, {len(pairs)} matched)"
        print(f"  {name:24s} {tag}")
    TRACKS.write_text(json.dumps(tracks, ensure_ascii=False, indent=1))
    print(f"\n{warped} warped, {identity} identity (unchanged). Wrote {TRACKS}")


if __name__ == "__main__":
    main()
