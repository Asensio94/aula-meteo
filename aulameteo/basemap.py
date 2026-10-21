"""One-off: build web/basemap.js (land, coastline, borders) from Natural Earth 1:50m, clipped to the domain.

Usage: python -m aulameteo.basemap   (downloads Natural Earth v5.1.2 GeoJSON, public domain)
"""
import json

import requests
from shapely.geometry import box, mapping, shape

from . import config

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/{}.geojson"
LAYERS = {"land": "ne_50m_land", "coast": "ne_50m_coastline", "borders": "ne_50m_admin_0_boundary_lines_land"}


def _round(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 2), round(coords[1], 2)]
    return [_round(c) for c in coords]


def build():
    clip = box(config.LON_MIN - 2, config.LAT_MIN - 2, config.LON_MAX + 2, config.LAT_MAX + 2)
    out = {}
    for key, name in LAYERS.items():
        src = requests.get(NE.format(name), timeout=120).json()
        feats = []
        for f in src["features"]:
            g = shape(f["geometry"]).intersection(clip)
            if g.is_empty:
                continue
            gj = mapping(g.simplify(0.02))
            gj = {"type": gj["type"], "coordinates": _round(gj["coordinates"])} if "coordinates" in gj else gj
            feats.append({"type": "Feature", "properties": {}, "geometry": gj})
        out[key] = {"type": "FeatureCollection", "features": feats}
    path = config.WEB / "basemap.js"
    path.write_text("window.BASEMAP = " + json.dumps(out, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"{path} {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
