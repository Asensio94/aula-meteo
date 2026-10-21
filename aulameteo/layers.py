"""Turn fields into map layers: GeoJSON contour lines and colour PNGs reprojected to Web Mercator.

The colour fields come on a regular latitude/longitude grid, but MapLibre draws an image
stretched linearly in Mercator space. Resampling the rows to equal Mercator spacing first
keeps the colours aligned with the contours all the way up to 75° N.
"""
import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from PIL import Image  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

from . import config  # noqa: E402

# Colour layers: discrete levels so the legend and the picture tell the same story.
# Values below the first level are transparent where `transparent_below` is set.
COLOUR_LAYERS = {
    "t850": {
        "name": "Temperatura 850 hPa", "unit": "°C", "field": "t850",
        "levels": list(range(-24, 30, 3)),
        "cmap": "RdYlBu_r", "transparent_below": False,
    },
    "jet250": {
        "name": "Viento 250 hPa (chorro)", "unit": "m/s", "field": "wind250",
        "levels": [30, 40, 50, 60, 70, 80, 90],
        "colors": ["#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#6a51a3", "#54278f", "#3f007d"],
        "transparent_below": True,
    },
    "precip": {
        "name": "Precipitación 12 h", "unit": "mm", "field": "precip12",
        "levels": [0.5, 1, 2, 5, 10, 20, 30, 50, 80, 120],
        "colors": ["#c7e9f5", "#9fd3ec", "#63b3e0", "#2f8ed1", "#1d6fb8", "#2ca25f", "#f5d02f",
                   "#f28e2b", "#d62728", "#9b1d6e"],
        "transparent_below": True,
    },
    "cape": {
        "name": "CAPE", "unit": "J/kg", "field": "cape",
        "levels": [100, 250, 500, 1000, 1500, 2000, 3000, 4000],
        "colors": ["#fff3b0", "#ffe066", "#fcbf49", "#f77f00", "#e85d04", "#d62828", "#9d0208", "#6a040f"],
        "transparent_below": True,
    },
}

CONTOURS = {
    "msl": {"field": "msl", "interval": 4, "bold_every": 5, "unit": "hPa"},   # bold 1000/1020…
    "z500": {"field": "z500", "interval": 4, "bold_every": 3, "unit": "dam"},  # bold 552/564…
}


def _mercator_y(lat):
    return np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def _to_mercator_rows(values, lats):
    """Resample rows (lats descending) so they are equally spaced in Mercator y."""
    y_src = _mercator_y(lats)[::-1]                      # ascending
    n_rows = int(round(len(lats) * (y_src[-1] - y_src[0]) / np.radians(lats[0] - lats[-1])))
    y_dst = np.linspace(y_src[-1], y_src[0], n_rows)     # top row first
    out = np.empty((n_rows, values.shape[1]), dtype=float)
    src = values[::-1]                                    # ascending lat to match y_src
    for j in range(values.shape[1]):
        out[:, j] = np.interp(y_dst, y_src, src[:, j])
    return out


def legend(spec):
    cmap = _cmap(spec)
    colours = [matplotlib.colors.to_hex(cmap(i)) for i in range(cmap.N)]
    return {"name": spec["name"], "unit": spec["unit"], "levels": spec["levels"], "colors": colours}


def _cmap(spec):
    n = len(spec["levels"])
    if "colors" in spec:
        return ListedColormap(spec["colors"])
    return ListedColormap(plt.get_cmap(spec["cmap"])(np.linspace(0, 1, n)))


def colour_png(da, spec) -> str:
    """Field -> RGBA PNG (Mercator rows) as a data: URI."""
    lats = da.latitude.values
    vals = _to_mercator_rows(da.values.astype(float), lats)
    levels = spec["levels"]
    cmap = _cmap(spec)
    norm = BoundaryNorm(levels + [levels[-1] + 1e9], cmap.N, extend="neither")
    rgba = cmap(norm(np.clip(vals, levels[0] if not spec["transparent_below"] else -1e9, None)))
    if spec["transparent_below"]:
        rgba[vals < levels[0], 3] = 0.0
    img = Image.fromarray((rgba * 255).astype(np.uint8), "RGBA")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def contour_geojson(da, interval, bold_every):
    vals = da.values
    lo = np.floor(np.nanmin(vals) / interval) * interval
    levels = np.arange(lo, np.nanmax(vals) + interval, interval)
    fig = plt.figure()
    cs = plt.contour(da.longitude.values, da.latitude.values, vals, levels=levels)
    feats = []
    for lev, segs in zip(cs.levels, cs.allsegs):
        bold = int(round(lev / interval)) % bold_every == 0
        for seg in segs:
            if len(seg) < 4:
                continue
            # A tenth of a grid cell is invisible at map zooms and halves the payload.
            line = LineString(seg).simplify(0.03)
            coords = np.round(np.asarray(line.coords), 2).tolist()
            feats.append({"type": "Feature", "properties": {"v": int(round(lev)), "bold": bold},
                          "geometry": {"type": "LineString", "coordinates": coords}})
    plt.close(fig)
    return {"type": "FeatureCollection", "features": feats}


def image_bounds():
    """Corner coordinates for a MapLibre image source (TL, TR, BR, BL)."""
    return [[config.LON_MIN, config.LAT_MAX], [config.LON_MAX, config.LAT_MAX],
            [config.LON_MAX, config.LAT_MIN], [config.LON_MIN, config.LAT_MIN]]


WIND_EVERY = 4  # 0.25° grid -> one arrow per degree; the page thins them out at low zoom


def wind_grid(s):
    """10 m wind on a 1° grid: speed in km/h and the direction it blows towards, in tens of degrees."""
    u = s["u10"].values[::WIND_EVERY, ::WIND_EVERY]
    v = s["v10"].values[::WIND_EVERY, ::WIND_EVERY]
    kmh = np.rint(np.hypot(u, v) * 3.6).astype(int)
    to_deg = np.rint((np.degrees(np.arctan2(u, v)) % 360) / 10).astype(int) % 36
    return {"kmh": kmh.ravel().tolist(), "dir10": to_deg.ravel().tolist()}


def wind_meta(ds):
    lats, lons = ds.latitude.values[::WIND_EVERY], ds.longitude.values[::WIND_EVERY]
    return {"lat0": float(lats[0]), "lon0": float(lons[0]), "dlat": float(lats[1] - lats[0]),
            "dlon": float(lons[1] - lons[0]), "ny": len(lats), "nx": len(lons)}


def build(ds):
    steps = []
    for k, h in enumerate(ds.step_h.values):
        s = ds.isel(step=k)
        step = {"step_h": int(h), "contours": {}, "images": {}}
        for key, spec in CONTOURS.items():
            step["contours"][key] = contour_geojson(s[spec["field"]], spec["interval"], spec["bold_every"])
        for key, spec in COLOUR_LAYERS.items():
            if key == "precip" and h == 0:
                continue  # no accumulation yet at the start of the run
            step["images"][key] = colour_png(s[spec["field"]], spec)
        if "u10" in s:
            step["wind"] = wind_grid(s)
        steps.append(step)
    return {"bounds": image_bounds(), "steps": steps,
            "wind": wind_meta(ds) if "u10" in ds else None,
            "legends": {k: legend(v) for k, v in COLOUR_LAYERS.items()}}
