"""Static configuration: domain, paths, forecast steps and focus regions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # raw downloads and state (gitignored)
SITE = ROOT / "site"          # generated website (open site/index.html; published to gh-pages)
CONCEPTS = ROOT / "concepts"  # hand-written concept cards (Markdown)
PROMPTS = ROOT / "prompts"
WEB = ROOT / "web"            # static assets copied into the site

# Europe + North Atlantic: Canarias to Cabo Norte, Iceland to Moscow.
LAT_MIN, LAT_MAX = 25.0, 75.0
LON_MIN, LON_MAX = -45.0, 50.0

# ECMWF IFS open data, 00 UTC run.
RUN_HOUR = 0
STEPS = [0, 12, 24, 36, 48, 60, 72]
SFC_PARAMS = ["msl", "2t", "tp", "mucape", "tcwv"]
PL_PARAMS = ["gh", "t", "u", "v"]
PL_LEVELS = [850, 500, 250]
WIND10_PARAMS = ["10u", "10v"]  # own file, so runs downloaded before it was added still work

# Zoom used by the second half of the daily explanation.
FOCUS = {
    "name": "península ibérica y Baleares",
    "lat": (35.5, 44.5),
    "lon": (-10.0, 4.5),
}

KEEP_GRIB_DAYS = 2
KEEP_SITE_DAYS = 180  # ~2 MB a day: about 360 MB on GitHub Pages (limit 1 GB)

# Headless Claude Code on the user's subscription ("opus", "sonnet" or a full model id).
CLAUDE_MODEL = "opus"
