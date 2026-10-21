"""Load the GRIB files into one cropped xarray Dataset with derived fields in friendly units."""
import warnings

import numpy as np
import xarray as xr

from . import config

warnings.filterwarnings("ignore", module="cfgrib")


def _open(path, **keys) -> xr.Dataset:
    ds = xr.open_dataset(path, engine="cfgrib",
                         backend_kwargs={"filter_by_keys": keys, "indexpath": ""})
    ds = ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180).sortby("longitude")
    ds = ds.drop_vars([c for c in ds.coords if c not in ds.dims])  # time/valid_time/surface…
    return ds.sel(latitude=slice(config.LAT_MAX, config.LAT_MIN),
                  longitude=slice(config.LON_MIN, config.LON_MAX))


def load(sfc_path, pl_path, wind10_path=None) -> xr.Dataset:
    sfc = {name: _open(sfc_path, shortName=short)[var]
           for name, short, var in [("msl", "msl", "msl"), ("t2m", "2t", "t2m"), ("tp", "tp", "tp"),
                                    ("cape", "mucape", "mucape"), ("tcwv", "tcwv", "tcwv")]}
    pl = _open(pl_path, typeOfLevel="isobaricInhPa")

    def lev(var, p):
        return pl[var].sel(isobaricInhPa=p, drop=True)

    tp_mm = sfc["tp"] * 1000.0  # m -> mm, accumulated since run start
    precip12 = tp_mm.diff("step").reindex(step=tp_mm.step).fillna(0.0).clip(min=0)

    u250, v250 = lev("u", 250), lev("v", 250)
    out = xr.Dataset({
        "msl": sfc["msl"] / 100.0,                    # hPa
        "t2m": sfc["t2m"] - 273.15,                   # °C
        "precip12": precip12,                         # mm in the previous 12 h
        "cape": sfc["cape"],                          # J/kg (most unstable)
        "tcwv": sfc["tcwv"],                          # kg/m² = mm of precipitable water
        "z500": lev("gh", 500) / 10.0,                # dam
        "t500": lev("t", 500) - 273.15,
        "t850": lev("t", 850) - 273.15,
        "z850": lev("gh", 850) / 10.0,
        "u250": u250, "v250": v250,
        "wind250": np.hypot(u250, v250),              # m/s
    })
    if wind10_path is not None and wind10_path.exists():
        w = _open(wind10_path, typeOfLevel="heightAboveGround")
        out["u10"], out["v10"] = w["u10"], w["v10"]
        out["wind10"] = np.hypot(w["u10"], w["v10"])  # m/s
    out["step_h"] = (out.step / np.timedelta64(1, "h")).astype(int)
    return out.load()
