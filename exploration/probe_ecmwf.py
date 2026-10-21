import time, os
from ecmwf.opendata import Client
c = Client(source="ecmwf", model="ifs", resol="0p25")
print("latest run:", c.latest(type="fc", step=0, param="msl"))
reqs = {
  "sfc": dict(type="fc", step=[0, 24, 48], param=["msl", "2t", "10u", "10v", "tp", "tcwv", "mucape"]),
  "pl":  dict(type="fc", step=[0, 24, 48], param=["gh", "t", "u", "v"], levelist=[850, 500, 250]),
}
for name, r in reqs.items():
    t = time.time()
    try:
        res = c.retrieve(target=f"data/{name}.grib2", **r)
        print(name, "ok", res.datetime, f"{os.path.getsize(f'data/{name}.grib2')/1e6:.1f} MB", f"{time.time()-t:.0f}s")
    except Exception as e:
        print(name, "FAIL", e)
