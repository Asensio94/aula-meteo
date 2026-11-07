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

# Regions the daily explanation zooms into, each with its own section on the page. "field" is the
# key of that section in Claude's JSON ("foco" stays for the Peninsula: days written before France
# was added only have that one). "detail" is a smaller area summarised inside the region.
FOCI = [
    {"key": "peninsula", "field": "foco", "name": "península ibérica y Baleares", "short": "Península",
     "lat": (35.5, 44.5), "lon": (-10.0, 4.5)},
    {"key": "francia", "field": "francia", "name": "Francia", "short": "Francia",
     "lat": (42.3, 51.1), "lon": (-5.0, 8.2),
     "detail": {"name": "París y alrededores", "lat": (48.6, 49.15), "lon": (1.75, 2.85)}},
]

KEEP_GRIB_DAYS = 2
GITHUB_USER = "Asensio94"  # owner of the repo; publish.py pushes with this account's gh login
KEEP_SITE_DAYS = 180  # ~2 MB a day: about 360 MB on GitHub Pages (limit 1 GB)

# Headless Claude Code on the user's subscription ("opus", "sonnet" or a full model id).
CLAUDE_MODEL = "opus"
