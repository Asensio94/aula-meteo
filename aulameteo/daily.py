"""Daily run: download, detect, draw, explain, publish.

    python -m aulameteo.daily                 # today
    python -m aulameteo.daily --date 2026-10-20
    python -m aulameteo.daily --reuse-text    # rebuild the page, keep the saved explanation
    python -m aulameteo.daily --rebuild-site  # only the shared pages (concepts, archive)
    python -m aulameteo.daily --publish       # any of the above, then push site/ to GitHub Pages
"""
import argparse
import datetime as dt
import json
import logging
import sys

from . import config, detect, explain, fetch, fields, layers, publish, quicklook, site

log = logging.getLogger("aulameteo")


def _setup_logging():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console is cp1252
    (config.DATA / "logs").mkdir(parents=True, exist_ok=True)
    logfile = config.DATA / "logs" / f"{dt.date.today():%Y-%m}.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(logfile, encoding="utf-8"), logging.StreamHandler(sys.stdout)])


def _recent_lessons(day, n=5):
    out = []
    for p in sorted((config.DATA / "days").glob("*/explain.json"), reverse=True):
        if p.parent.name >= day.isoformat():
            continue
        out.append(json.loads(p.read_text(encoding="utf-8"))["leccion"]["concepto"])
        if len(out) == n:
            break
    return out


def run(day: dt.date, reuse_text=False):
    generated = dt.datetime.now(dt.UTC).replace(tzinfo=None, second=0, microsecond=0)
    grib = fetch.fetch_ecmwf(day)
    run_time = grib["run"]
    if run_time.date() != day:  # today's run is not out yet: the page is yesterday's, keep its text
        log.warning("Run for %s not available; rebuilding %s", day, run_time.date())
        reuse_text = True
    day = run_time.date()
    out = config.DATA / "days" / day.isoformat()
    out.mkdir(parents=True, exist_ok=True)

    log.info("Loading fields for run %s", run_time)
    ds = fields.load(grib["sfc"], grib["pl"], grib.get("wind10"))
    detections = detect.detect_all(ds)
    (out / "detections.json").write_text(json.dumps(detections, ensure_ascii=False), encoding="utf-8")
    log.info("Detected %s features per step", [len(d["features"]) for d in detections])

    layers_data = layers.build(ds)
    charts = quicklook.render(ds, run_time, detections, out)

    text_path = out / "explain.json"
    text = json.loads(text_path.read_text(encoding="utf-8")) if reuse_text and text_path.exists() else None
    if text:  # rebuilding: keep the time and the DWD chart the text was written with
        meta = text["_meta"]
        generated = dt.datetime.fromisoformat(meta.get("generated") or f"{day}T09:00")
        dwd_valid = dt.datetime.fromisoformat(meta["dwd_valid"]) if meta.get("dwd_valid") else run_time
        dwd = fetch.fetch_dwd_analysis(out, valid_at=dwd_valid)
        sat_time = generated - dt.timedelta(minutes=40 + generated.minute % 10)
    else:
        dwd = fetch.fetch_dwd_analysis(out)
        sat_time = generated - dt.timedelta(minutes=40 + generated.minute % 10)
        sat = fetch.fetch_satellite(out, sat_time)  # only Claude looks at it
        text = explain.explain(day, run_time, detections, charts, dwd, sat, _recent_lessons(day))
        text["_meta"]["generated"] = generated.isoformat(timespec="minutes")
        text["_meta"]["dwd_valid"] = dwd["valid"].isoformat(timespec="minutes") if dwd else None
        text_path.write_text(json.dumps(text, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("Explanation: %s (%s s)", text["titular"], text["_meta"]["duration_s"])

    publish.prune_old_days()
    site.build_day(day, run_time, detections, layers_data, text, dwd, sat_time, generated)
    fetch.prune_old_grib()
    log.info("Done: %s", config.SITE / "days" / day.isoformat() / "index.html")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today())
    ap.add_argument("--reuse-text", action="store_true")
    ap.add_argument("--rebuild-site", action="store_true")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    _setup_logging()
    try:
        if args.rebuild_site:
            site.rebuild_shared()
        else:
            run(args.date, reuse_text=args.reuse_text)
    except Exception:
        log.exception("Daily run failed")
        sys.exit(1)
    if args.publish:
        try:
            publish.publish(f"Site as of {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC")
        except Exception:
            log.exception("Publishing failed (the local site is up to date)")
            sys.exit(1)


if __name__ == "__main__":
    main()
