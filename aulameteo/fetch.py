"""Downloads: ECMWF open data (GRIB), DWD surface analysis chart, a Meteosat snapshot."""
import datetime as dt
import logging
import re
import shutil
import time

import requests
from ecmwf.opendata import Client

from . import config

log = logging.getLogger(__name__)

DWD_DIR = "https://opendata.dwd.de/weather/charts/analysis/"
DWD_RE = re.compile(r'href="([^"]*ana_bwkman_dwdna_O_000000_000000_(\d{12})_WV12\.png)"')
EUMETSAT_WMS = "https://view.eumetsat.int/geoserver/wms"


def fetch_ecmwf(run_date: dt.date) -> dict:
    """Download the 00 UTC run of `run_date`, falling back to the previous day if not out yet.

    Each file is fetched only if missing, so a field added later is downloaded for a run on its own.
    """
    client = Client(source="ecmwf", model="ifs", resol="0p25")
    files = {"sfc": dict(param=config.SFC_PARAMS), "wind10": dict(param=config.WIND10_PARAMS),
             "pl": dict(param=config.PL_PARAMS, levelist=config.PL_LEVELS)}
    for date in (run_date, run_date - dt.timedelta(days=1)):
        out = config.DATA / "grib" / date.strftime("%Y%m%d")
        paths = {name: out / f"{name}.grib2" for name in files}
        missing = [name for name, p in paths.items() if not p.exists()]
        if not missing:
            log.info("ECMWF %s already downloaded", date)
            return {"run": dt.datetime.combine(date, dt.time(config.RUN_HOUR)), **paths}
        out.mkdir(parents=True, exist_ok=True)
        common = dict(date=date.strftime("%Y%m%d"), time=config.RUN_HOUR, type="fc", step=config.STEPS)
        try:
            for name in missing:
                log.info("Downloading ECMWF %s %s", date, name)
                client.retrieve(target=str(paths[name]), **files[name], **common)
        except Exception as exc:  # run not published yet -> try the previous day
            log.warning("ECMWF run %s not available: %s", date, exc)
            for name in missing:
                paths[name].unlink(missing_ok=True)
            continue
        return {"run": dt.datetime.combine(date, dt.time(config.RUN_HOUR)), **paths}
    raise RuntimeError("No ECMWF 00 UTC run available for today or yesterday")


def fetch_dwd_analysis(dest_dir, valid_at: dt.datetime | None = None) -> dict | None:
    """DWD hand-analysed surface chart (Europe/North Atlantic, with fronts): the most recent one, or
    the last one valid at or before `valid_at` when rebuilding a past day (the server keeps ~2 days)."""
    try:
        listing = requests.get(DWD_DIR, timeout=30).text
        files = sorted(DWD_RE.findall(listing), key=lambda m: m[1])
        if valid_at is not None:
            files = [f for f in files if f[1] <= valid_at.strftime("%Y%m%d%H%M")]
        if not files:
            return None
        name, stamp = files[-1]
        png = requests.get(DWD_DIR + name, timeout=60)
        png.raise_for_status()
    except requests.RequestException as exc:
        log.warning("DWD analysis unavailable: %s", exc)
        return None
    path = dest_dir / "dwd_analysis.png"
    path.write_bytes(png.content)
    valid = dt.datetime.strptime(stamp, "%Y%m%d%H%M")
    return {"path": path, "valid": valid}


def fetch_satellite(dest_dir, when: dt.datetime, layer="mtg_fd:ir105_hrfi") -> dict | None:
    """Meteosat image over the whole domain at `when` (UTC), for the AI to look at."""
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap", "layers": layer, "styles": "",
        "crs": "EPSG:4326", "format": "image/png", "width": 1140, "height": 600,
        "bbox": f"{config.LAT_MIN},{config.LON_MIN},{config.LAT_MAX},{config.LON_MAX}",
        "time": when.strftime("%Y-%m-%dT%H:%M:00Z"),
    }
    for attempt in range(3):  # the server answers 503 now and then; a short wait is usually enough
        if attempt:
            time.sleep(20 * attempt)
        try:
            r = requests.get(EUMETSAT_WMS, params=params, timeout=90)
            r.raise_for_status()
        except requests.RequestException as exc:
            log.warning("EUMETSAT image unavailable (try %d): %s", attempt + 1, exc)
            continue
        if r.headers.get("content-type", "").startswith("image/"):
            break
        log.warning("EUMETSAT returned %s (try %d)", r.headers.get("content-type"), attempt + 1)
    else:
        return None
    path = dest_dir / "satellite_ir.png"
    path.write_bytes(r.content)
    return {"path": path, "valid": when, "layer": layer}


def prune_old_grib(keep_days: int = config.KEEP_GRIB_DAYS) -> None:
    root = config.DATA / "grib"
    if not root.exists():
        return
    for d in sorted(p for p in root.iterdir() if p.is_dir())[:-keep_days]:
        shutil.rmtree(d, ignore_errors=True)
