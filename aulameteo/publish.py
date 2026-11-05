"""Publish site/ to GitHub Pages and keep it within size.

The site goes to the gh-pages branch as a single commit with no parent, force-pushed every day: each
page carries about 2 MB of map data, and keeping that history would grow the repo by ~700 MB a year.
The code lives on main; site/ is gitignored there.
"""
import datetime as dt
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

BRANCH = "gh-pages"


def prune_old_days(today: dt.date | None = None):
    """Drop day pages older than KEEP_SITE_DAYS (the texts stay in data/days)."""
    cutoff = (today or dt.date.today()) - dt.timedelta(days=config.KEEP_SITE_DAYS)
    root = config.SITE / "days"
    for d in root.iterdir() if root.exists() else []:
        try:
            day = dt.date.fromisoformat(d.name)
        except ValueError:
            continue
        if day < cutoff:
            shutil.rmtree(d)
            log.info("Removed old page %s", d.name)


def _git(*args, env=None, options=()) -> str:
    # GIT_TERMINAL_PROMPT / GCM_INTERACTIVE: the scheduled task has nobody to answer a login prompt
    env = {**(env or os.environ), "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    proc = subprocess.run(["git", "--git-dir", str(config.ROOT / ".git"), "--work-tree", str(config.SITE),
                           *options, *args],
                          cwd=config.SITE, env=env, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _gh_token() -> str | None:
    """The gh CLI login of the repo owner (None if gh is missing or has no login for that account)."""
    gh = shutil.which("gh")
    if not gh:
        return None
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}  # the stored login
    proc = subprocess.run([gh, "auth", "token", "-h", "github.com", "-u", config.GITHUB_USER],
                          env=env, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def _push_auth() -> tuple[dict, tuple]:
    """Push with gh's login instead of the Windows credential manager, whose token lapsed unnoticed for a
    week (Oct 2026): one login to keep alive, and `gh auth login` fixes both. The token goes through the
    environment, never the command line."""
    token = _gh_token()
    if not token:
        return os.environ, ()
    helper = f'!f() {{ echo username={config.GITHUB_USER}; echo "password=$AULA_PUSH_TOKEN"; }}; f'
    return {**os.environ, "AULA_PUSH_TOKEN": token}, ("-c", "credential.helper=", "-c", f"credential.helper={helper}")


def publish(message: str):
    """Snapshot site/ into a fresh commit (own index file, so main's index is untouched) and push it."""
    (config.SITE / ".nojekyll").touch()  # serve the files as they are, no Jekyll build
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git("add", "--all", ".", env=env)
        tree = _git("write-tree", env=env)
    commit = _git("commit-tree", tree, "-m", message)
    env, options = _push_auth()
    try:
        _git("push", "--force", "--quiet", "origin", f"{commit}:refs/heads/{BRANCH}", env=env, options=options)
    except RuntimeError as exc:
        raise RuntimeError(f"{exc}\nThe GitHub login has probably expired. Log in again as {config.GITHUB_USER} "
                           "with: gh auth login -h github.com   and then: .\\run_daily.ps1 --rebuild-site") from None
    log.info("Published %s to %s", commit[:8], BRANCH)
