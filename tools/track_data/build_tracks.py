#!/usr/bin/env python3
"""Build backend/app/data/tracks.json by merging the cross-checked corner data
with real circuit geometry from bacinger/f1-circuits (MIT).

Geometry → a normalized SVG path (equirectangular projection with a cos(lat)
correction, fit to a 1000×1000 viewBox, Y flipped for SVG). Run:

    curl -sSL -o /tmp/f1-circuits.geojson \\
        https://raw.githubusercontent.com/bacinger/f1-circuits/master/f1-circuits.geojson
    python tools/track_data/build_tracks.py
"""
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORNERS = ROOT / "backend" / "app" / "data" / "track_corners.json"
GEOJSON = pathlib.Path("/tmp/f1-circuits.geojson")
OUT = ROOT / "backend" / "app" / "data" / "tracks.json"

# Our track name (F1 24/25 Lookups.cs) -> bacinger circuit id. None = no clean
# outline (the in-game "Short" configs reuse a subset; Hanoi never raced).
GEO_ID = {
    "Melbourne": "au-1953", "Paul Ricard": "fr-1969", "Shanghai": "cn-2004",
    "Sakhir (Bahrain)": "bh-2002", "Catalunya": "es-1991", "Monaco": "mc-1929",
    "Montreal": "ca-1978", "Silverstone": "gb-1948", "Hockenheim": "de-1932",
    "Hungaroring": "hu-1986", "Spa": "be-1925", "Monza": "it-1922",
    "Singapore": "sg-2008", "Suzuka": "jp-1962", "Abu Dhabi": "ae-2009",
    "Texas (COTA)": "us-2012", "Brazil (Interlagos)": "br-1940",
    "Austria (Red Bull Ring)": "at-1969", "Sochi": "ru-2014", "Mexico": "mx-1962",
    "Baku": "az-2016", "Zandvoort": "nl-1948", "Imola": "it-1953",
    "Portimao": "pt-2008", "Jeddah": "sa-2021", "Miami": "us-2022",
    "Las Vegas": "us-2023", "Losail (Qatar)": "qa-2004",
    "Sakhir Short": None, "Silverstone Short": None, "Texas Short": None,
    "Suzuka Short": None, "Hanoi": None,
}

SIZE = 1000
PAD = 48


def project(coords):
    """lon/lat LineString -> (svg_path, start_point) fit to a SIZE×SIZE box."""
    mean_lat = sum(lat for _, lat in coords) / len(coords)
    kx = math.cos(math.radians(mean_lat))
    planar = [(lon * kx, lat) for lon, lat in coords]
    xs = [p[0] for p in planar]
    ys = [p[1] for p in planar]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    w, h = max_x - min_x, max_y - min_y
    avail = SIZE - 2 * PAD
    scale = avail / max(w, h)
    off_x = PAD + (avail - w * scale) / 2
    off_y = PAD + (avail - h * scale) / 2
    pts = [
        (round(off_x + (x - min_x) * scale, 1), round(off_y + (max_y - y) * scale, 1))
        for x, y in planar
    ]
    d = "M" + " L".join(f"{x},{y}" for x, y in pts) + " Z"
    return d, {"x": pts[0][0], "y": pts[0][1]}


def main():
    corners = json.loads(CORNERS.read_text())
    geo = {f["properties"]["id"]: f for f in json.loads(GEOJSON.read_text())["features"]}

    out = {}
    mapped = 0
    for name, info in corners.items():
        if name.startswith("_"):
            continue
        entry = {
            "name": name,
            "length_m": info.get("length_m"),
            "drs_zones": info.get("drs_zones"),
            "record": info.get("record"),
            "corner_count": len(info["corners"]),
            "corners": [{"n": i + 1, "name": nm} for i, nm in enumerate(info["corners"])],
            "map": None,
        }
        gid = GEO_ID.get(name)
        if gid and gid in geo:
            d, start = project(geo[gid]["geometry"]["coordinates"])
            entry["map"] = {"view_box": f"0 0 {SIZE} {SIZE}", "path": d, "start": start, "source_id": gid}
            mapped += 1
        out[name] = entry

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"wrote {OUT} — {len(out)} tracks, {mapped} with maps")
    z = out["Zandvoort"]
    print(f"  Zandvoort: {z['corner_count']} corners, map={'yes' if z['map'] else 'no'}, "
          f"path_len={len(z['map']['path']) if z['map'] else 0} chars")


if __name__ == "__main__":
    main()
