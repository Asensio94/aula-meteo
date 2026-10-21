"""Find the synoptic features of each forecast step: the facts the AI explanation is built on.

All thresholds are deliberately simple and documented, because they are part of what the
app teaches (each feature carries the concept slug that explains it).
"""
import numpy as np
from scipy import ndimage

from . import config
from .places import describe

GRID = 0.25  # degrees


def _coords(da):
    return da.latitude.values, da.longitude.values


def _blob_centres(mask, values, pick):
    """One point per connected blob of `mask` (plateaus give many equal extrema)."""
    labels, n = ndimage.label(mask)
    out = []
    for k in range(1, n + 1):
        idx = np.argwhere(labels == k)
        vals = values[idx[:, 0], idx[:, 1]]
        i, j = idx[pick(vals)]
        out.append((i, j))
    return out


def _ring_mean(a, i, j, r_in, r_out):
    ii, jj = np.ogrid[: a.shape[0], : a.shape[1]]
    d = np.hypot(ii - i, jj - j)
    ring = (d >= r_in) & (d <= r_out)
    return float(a[ring].mean())


def _closed(a, i, j, threshold, sign):
    """Is the contour `threshold` around (i, j) closed inside the domain?

    sign=+1 for lows (region a < threshold), -1 for highs (region a > threshold).
    """
    region = (a < threshold) if sign > 0 else (a > threshold)
    labels, _ = ndimage.label(region)
    k = labels[i, j]
    if k == 0:
        return False
    blob = labels == k
    touches_edge = blob[0].any() or blob[-1].any() or blob[:, 0].any() or blob[:, -1].any()
    return not touches_edge


def _point(kind, concept, lat, lon, **extra):
    extra = {k: (float(v) if isinstance(v, np.floating) else v) for k, v in extra.items()}
    return {"kind": kind, "concept": concept, "lat": round(float(lat), 2),
            "lon": round(float(lon), 2), "where": describe(lat, lon), **extra}


def in_scope(f):
    """The rectangle includes the Middle East and the Sahara; leave them out of the story."""
    return not ((f["lon"] > 36 and f["lat"] < 42) or f["lat"] < 27)


def pressure_centres(msl):
    """Surface lows (B) and highs (A): local extrema at least 3/2 hPa off their surroundings."""
    a = ndimage.gaussian_filter(msl.values, 1.0)
    lats, lons = _coords(msl)
    found = []
    for kind, fn, pick, sign, min_depth in [
        ("borrasca", ndimage.minimum_filter, np.argmin, +1, 4.0),
        ("anticiclon", ndimage.maximum_filter, np.argmax, -1, 3.0),
    ]:
        mask = a == fn(a, size=21, mode="nearest")
        mask[:4], mask[-4:], mask[:, :4], mask[:, -4:] = False, False, False, False
        for i, j in _blob_centres(mask, a, pick):
            depth = sign * (_ring_mean(a, i, j, 20, 32) - a[i, j])
            if depth < min_depth:
                continue
            found.append(_point(kind, kind, lats[i], lons[j], hpa=round(float(msl.values[i, j]), 1),
                                contrast_hpa=round(float(depth), 1)))
    # Keep the most marked ones: a beginner's map, not an exhaustive analysis.
    lows = sorted((f for f in found if f["kind"] == "borrasca"), key=lambda f: -f["contrast_hpa"])
    highs = sorted((f for f in found if f["kind"] == "anticiclon"), key=lambda f: -f["contrast_hpa"])
    return lows[:7] + highs[:5]


def upper_features(z500, u250):
    """500 hPa closed lows (DANA / cold low), closed highs, and open troughs/ridges."""
    a = ndimage.gaussian_filter(z500.values, 1.0)
    lats, lons = _coords(z500)
    feats = []
    closed_lows = []
    for i, j in _blob_centres(_extrema(a, ndimage.minimum_filter), a, np.argmin):
        if not _closed(a, i, j, a[i, j] + 4.0, +1):     # one 4-dam contour around it
            continue
        # Cut off from the westerlies if the flow on its south side is not westerly.
        i_south = min(i + 20, a.shape[0] - 1)
        u_south = float(u250.values[i_south, max(j - 8, 0): j + 9].mean())
        cut_off = u_south < 5.0 and lats[i] < 55
        kind = "dana" if cut_off else "baja-fria-en-altura"
        concept = "dana" if cut_off else "geopotencial-500"
        feats.append(_point(kind, concept, lats[i], lons[j], dam=round(float(z500.values[i, j]), 1),
                            westerly_wind_south_ms=round(u_south, 1)))
        closed_lows.append((i, j))
    for i, j in _blob_centres(_extrema(a, ndimage.maximum_filter), a, np.argmax):
        if lats[i] > 45 and _closed(a, i, j, a[i, j] - 4.0, -1):
            south_low = any(ii > i and abs(jj - j) < 100 for ii, jj in closed_lows)
            feats.append(_point("bloqueo" if south_low else "alta-en-altura",
                                "bloqueo" if south_low else "vaguada-y-dorsal",
                                lats[i], lons[j], dam=round(float(z500.values[i, j]), 1),
                                closed_low_to_south=south_low))
    # Curvature of the height field: Laplacian > 0 = cyclonic (trough), < 0 = ridge.
    lap = ndimage.laplace(ndimage.gaussian_filter(z500.values, 4.0))
    thr = np.percentile(np.abs(lap), 97)
    for kind, fn, pick, sign in [("vaguada", ndimage.maximum_filter, np.argmax, 1),
                                 ("dorsal", ndimage.minimum_filter, np.argmin, -1)]:
        mask = (lap == fn(lap, size=41, mode="nearest")) & (sign * lap > thr)
        mask[:8], mask[-8:], mask[:, :8], mask[:, -8:] = False, False, False, False
        for i, j in _blob_centres(mask, lap, pick):
            near_closed = any(np.hypot(i - ii, j - jj) < 24 for ii, jj in closed_lows)
            if kind == "vaguada" and near_closed:
                continue
            feats.append(_point(kind, "vaguada-y-dorsal", lats[i], lons[j],
                                dam=round(float(z500.values[i, j]), 1)))
    return feats


def _extrema(a, fn):
    mask = a == fn(a, size=21, mode="nearest")
    mask[:4], mask[-4:], mask[:, :4], mask[:, -4:] = False, False, False, False
    return mask


def jet_streaks(wind250, top=3):
    """Cores of the jet stream at 250 hPa (≥ 50 m/s ≈ 180 km/h)."""
    a = wind250.values
    lats, lons = _coords(wind250)
    labels, n = ndimage.label(a >= 50)
    cores = []
    for k in range(1, n + 1):
        idx = np.argwhere(labels == k)
        if len(idx) < 30:
            continue
        i, j = idx[np.argmax(a[idx[:, 0], idx[:, 1]])]
        cores.append(_point("chorro", "corriente-en-chorro", lats[i], lons[j],
                            max_ms=round(float(a[i, j]), 1), max_kmh=round(float(a[i, j]) * 3.6),
                            lon_span=[round(float(lons[idx[:, 1].min()]), 1),
                                      round(float(lons[idx[:, 1].max()]), 1)]))
    return sorted(cores, key=lambda c: -c["max_ms"])[:top]


def hotspots(da, threshold, kind, concept, unit, top=3, min_cells=8):
    """Largest values of a scalar field (CAPE, precipitation) above a threshold."""
    a = da.values
    lats, lons = _coords(da)
    labels, n = ndimage.label(a >= threshold)
    spots = []
    for k in range(1, n + 1):
        idx = np.argwhere(labels == k)
        if len(idx) < min_cells:
            continue
        i, j = idx[np.argmax(a[idx[:, 0], idx[:, 1]])]
        spots.append(_point(kind, concept, lats[i], lons[j], **{f"max_{unit}": round(float(a[i, j]))},
                            area_km2=int(round(len(idx) * (27.8 * GRID / 0.25) ** 2 * np.cos(np.radians(lats[i])), -2))))
    spots = [p for p in spots if in_scope(p)]
    return sorted(spots, key=lambda s: -s[f"max_{unit}"])[:3]


def focus_summary(ds_step):
    f = config.FOCUS
    box = ds_step.sel(latitude=slice(f["lat"][1], f["lat"][0]), longitude=slice(f["lon"][0], f["lon"][1]))
    out = {
        "region": f["name"],
        "t850_c": {"min": round(float(box.t850.min()), 1), "max": round(float(box.t850.max()), 1),
                   "mean": round(float(box.t850.mean()), 1)},
        "t2m_c": {"min": round(float(box.t2m.min()), 1), "max": round(float(box.t2m.max()), 1)},
        "msl_hpa": {"min": round(float(box.msl.min()), 1), "max": round(float(box.msl.max()), 1)},
        "precip12_mm_max": round(float(box.precip12.max()), 1),
        "cape_max": round(float(box.cape.max())),
        "wind250_max_ms": round(float(box.wind250.max()), 1),
    }
    if "wind10" in box:  # mean 10 m wind from the model, not gusts
        out["wind10_max_kmh"] = round(float(box.wind10.max()) * 3.6)
    return out


def detect_step(ds, step_h):
    s = ds.sel(step=ds.step[list(ds.step_h.values).index(step_h)])
    feats = pressure_centres(s.msl) + upper_features(s.z500, s.u250) + jet_streaks(s.wind250)
    feats += hotspots(s.cape, 1000, "inestabilidad", "inestabilidad-y-cape", "jkg", top=6)
    if step_h > 0:
        feats += hotspots(s.precip12, 20, "lluvia-intensa", "precipitacion", "mm", top=6)
    feats = [f for f in feats if in_scope(f)]
    return {"step_h": int(step_h), "features": feats, "focus": focus_summary(s)}


def detect_all(ds):
    return [detect_step(ds, int(h)) for h in ds.step_h.values]
