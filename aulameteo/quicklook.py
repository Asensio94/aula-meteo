"""Static model charts for the AI to look at (the web map is interactive; the model needs pictures)."""
import datetime as dt
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import config  # noqa: E402
from .layers import COLOUR_LAYERS, _cmap  # noqa: E402
from matplotlib.colors import BoundaryNorm  # noqa: E402

PANEL_STEPS = [0, 24, 48, 72]


def _coast():
    text = (config.WEB / "basemap.js").read_text(encoding="utf-8")
    data = json.loads(text[text.index("{"): text.rindex("}") + 1])
    lines = []
    for f in data["coast"]["features"]:
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        lines += [np.array(p) for p in parts]
    return lines


def _filled(ax, da, key):
    spec = COLOUR_LAYERS[key]
    levels = spec["levels"]
    vals = da.values
    if spec["transparent_below"]:
        vals = np.where(vals < levels[0], np.nan, vals)
    norm = BoundaryNorm(levels + [levels[-1] + 1e9], len(levels))
    ax.contourf(da.longitude, da.latitude, vals, levels=levels + [levels[-1] + 1e9],
                cmap=_cmap(spec), norm=norm)


def _panel_grid(title):
    fig, axes = plt.subplots(2, 2, figsize=(16, 10.5), constrained_layout=True)
    fig.suptitle(title, fontsize=14)
    return fig, axes.ravel()


def render(ds, run, detections, out_dir):
    """Two 2×2 figures (+0/+24/+48/+72 h): surface and upper air. Returns their paths."""
    coast = _coast()
    by_step = {d["step_h"]: d for d in detections}
    paths = {}
    for name, title in [("modelo_superficie", "Superficie: presión (isobaras cada 4 hPa) y precipitación 12 h (mm)"),
                        ("modelo_altura", "Altura: geopotencial 500 hPa (dam, negro), T 850 hPa (color) y chorro ≥ 50 m/s (morado)")]:
        fig, axes = _panel_grid(f"ECMWF IFS, pasada {run:%d/%m/%Y %H} UTC. {title}")
        for ax, h in zip(axes, PANEL_STEPS):
            s = ds.sel(step=ds.step[list(ds.step_h.values).index(h)])
            valid = run + dt.timedelta(hours=int(h))
            if name == "modelo_superficie":
                if h > 0:
                    _filled(ax, s.precip12, "precip")
                cs = ax.contour(s.longitude, s.latitude, s.msl, levels=np.arange(940, 1060, 4),
                                colors="k", linewidths=0.6)
                ax.clabel(cs, fontsize=6, fmt="%d")
                for f in by_step[h]["features"]:
                    if f["kind"] in ("borrasca", "anticiclon"):
                        ax.text(f["lon"], f["lat"], "B" if f["kind"] == "borrasca" else "A",
                                color="red" if f["kind"] == "borrasca" else "blue",
                                fontsize=15, weight="bold", ha="center", va="center")
            else:
                _filled(ax, s.t850, "t850")
                cs = ax.contour(s.longitude, s.latitude, s.z500, levels=np.arange(480, 600, 4),
                                colors="k", linewidths=0.7)
                ax.clabel(cs, fontsize=6, fmt="%d")
                ax.contour(s.longitude, s.latitude, s.wind250, levels=[50, 70],
                           colors="#5b2a86", linewidths=[1.2, 2.0])
            for line in coast:
                ax.plot(line[:, 0], line[:, 1], color="#555", linewidth=0.4)
            ax.set_xlim(config.LON_MIN, config.LON_MAX)
            ax.set_ylim(config.LAT_MIN, config.LAT_MAX)
            ax.set_title(f"+{h} h  →  válido {valid:%d/%m %H} UTC", fontsize=11)
            ax.tick_params(labelsize=7)
        path = out_dir / f"{name}.png"
        fig.savefig(path, dpi=80)
        plt.close(fig)
        paths[name] = path
    return paths
