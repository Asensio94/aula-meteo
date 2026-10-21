import json, os, warnings
import numpy as np, xarray as xr, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.ndimage import minimum_filter, maximum_filter
warnings.filterwarnings("ignore")
BOX = dict(latitude=slice(65, 25), longitude=slice(-35, 25))  # N Atlantic + Europe
def open_(f, **kw):
    ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs=dict(filter_by_keys=kw, indexpath=""))
    ds = ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180).sortby("longitude")
    return ds.sel(**BOX)
msl = open_("data/sfc.grib2", shortName="msl")["msl"].isel(step=0) / 100
z5 = open_("data/pl.grib2", shortName="gh", level=500)["gh"].isel(step=0) / 10  # dam
t8 = open_("data/pl.grib2", shortName="t", level=850)["t"].isel(step=0) - 273.15
print("grid", msl.shape, "valid", str(msl.valid_time.values)[:16])

def extrema(da, size, fn, label):
    a = da.values; m = (a == fn(a, size=size, mode="nearest"))
    m[:2,:]=m[-2:,:]=m[:,:2]=m[:,-2:]=False
    return [dict(type=label, lat=float(da.latitude[i]), lon=float(da.longitude[j]), value=round(float(a[i,j]),1)) for i,j in zip(*np.where(m))]
lows = extrema(msl, 41, minimum_filter, "L"); highs = extrema(msl, 41, maximum_filter, "H")
lows5 = extrema(z5, 41, minimum_filter, "low500")
print("surface lows:", lows); print("surface highs:", highs); print("500 hPa lows (possible cut-off/trough):", lows5)

# contours -> GeoJSON lines, to size the interactive layer
def contours_geojson(da, levels):
    cs = plt.contour(da.longitude, da.latitude, da.values, levels=levels)
    feats = []
    for lev, segs in zip(cs.levels, cs.allsegs):
        for s in segs:
            if len(s) > 3:
                feats.append({"type":"Feature","properties":{"v":float(lev)},
                    "geometry":{"type":"LineString","coordinates":np.round(s,2).tolist()}})
    plt.close(); return {"type":"FeatureCollection","features":feats}
gj = contours_geojson(msl, np.arange(960, 1050, 4))
os.makedirs("data/out", exist_ok=True)
json.dump(gj, open("data/out/isobars.json","w"), separators=(",",":"))
print("isobars geojson KB:", os.path.getsize("data/out/isobars.json")//1024, "features", len(gj["features"]))
# colour field as PNG overlay
plt.imsave("data/out/t850.png", t8.values, cmap="RdYlBu_r", vmin=-20, vmax=25, origin="upper")
print("t850 png KB:", os.path.getsize("data/out/t850.png")//1024)
# quick look figure
fig, ax = plt.subplots(figsize=(10,7))
ax.contourf(t8.longitude, t8.latitude, t8, levels=np.arange(-20,26,2.5), cmap="RdYlBu_r")
cs=ax.contour(z5.longitude, z5.latitude, z5, levels=np.arange(500,600,4), colors="k", linewidths=0.8); ax.clabel(cs, fontsize=7)
cs=ax.contour(msl.longitude, msl.latitude, msl, levels=np.arange(960,1050,4), colors="w", linewidths=0.6)
for p in lows: ax.text(p["lon"],p["lat"],"B",color="red",fontsize=16,weight="bold",ha="center")
for p in highs: ax.text(p["lon"],p["lat"],"A",color="blue",fontsize=16,weight="bold",ha="center")
ax.set_title(f"ECMWF IFS {str(msl.valid_time.values)[:16]}  T850 (color), Z500 (negro), PMSL (blanco)")
fig.savefig("data/out/quicklook.png", dpi=90, bbox_inches="tight")
