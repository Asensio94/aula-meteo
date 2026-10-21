"""Ask Claude (headless Claude Code, on the user's subscription) to explain the day.

The call is isolated from the user's own setup: custom system prompt, no settings, no MCP servers,
no skills, only the Read tool, and a working directory outside the projects tree so that no
CLAUDE.md is picked up. The model reads hechos.json and the images from that directory.
"""
import datetime as dt
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import config
from .concepts import LINK_RE, load_cards

log = logging.getLogger(__name__)

STORY_STEPS = [0, 24, 48, 72]
MAP_LAYERS = {"msl": "Presión en superficie", "z500": "Geopotencial 500 hPa", "t850": "Temperatura 850 hPa",
              "jet250": "Viento 250 hPa (chorro)", "precip": "Precipitación 12 h", "cape": "CAPE",
              "wind10": "Viento a 10 m (flechas)", "sat": "Satélite infrarrojo",
              "satwv": "Satélite vapor de agua", "satgeo": "Satélite color (de día)"}

SCHEMA = {
    "type": "object",
    "properties": {
        "titular": {"type": "string"},
        "entradilla": {"type": "string"},
        "europa": {"type": "string"},
        "foco": {"type": "string"},
        "leccion": {"type": "object",
                    "properties": {"concepto": {"type": "string"}, "texto": {"type": "string"}},
                    "required": ["concepto", "texto"]},
        "conceptos": {"type": "array", "items": {"type": "string"}},
        "preguntas": {"type": "array", "items": {
            "type": "object",
            "properties": {"pregunta": {"type": "string"},
                           "opciones": {"type": "array", "items": {"type": "string"}},
                           "correcta": {"type": "integer"}, "explicacion": {"type": "string"}},
            "required": ["pregunta", "opciones", "correcta", "explicacion"]}},
    },
    "required": ["titular", "entradilla", "europa", "foco", "leccion", "conceptos", "preguntas"],
}


def _claude_exe() -> str:
    """The scheduled task may run with a shorter PATH; fall back to the per-user install."""
    found = shutil.which("claude")
    if found:
        return found
    local = Path.home() / ".local" / "bin" / "claude.exe"
    return str(local) if local.exists() else "claude"


def work_dir(day: dt.date) -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "aula-meteo" / "work" / day.isoformat()
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    return base


def facts(day, run, detections, dwd, sat, recent_lessons):
    cards = load_cards()
    return {
        "fecha_del_dia": day.isoformat(),
        "pasada_modelo": f"{run:%Y-%m-%d %H} UTC (ECMWF IFS 0,25°)",
        "region_foco": config.FOCUS["name"],
        "pasos": [{"paso_h": d["step_h"],
                   "valido_utc": f"{run + dt.timedelta(hours=d['step_h']):%Y-%m-%d %H:%M}",
                   "sistemas": d["features"], "foco": d["focus"]}
                  for d in detections if d["step_h"] in STORY_STEPS],
        # the focus summary is small, so it goes in every 12 h step: rain often peaks between story steps
        "foco_cada_12h": [{"paso_h": d["step_h"],
                           "valido_utc": f"{run + dt.timedelta(hours=d['step_h']):%Y-%m-%d %H:%M}",
                           **d["focus"]} for d in detections],
        "analisis_dwd_valido_utc": f"{dwd['valid']:%Y-%m-%d %H:%M}" if dwd else None,
        "satelite_valido_utc": f"{sat['valid']:%Y-%m-%d %H:%M}" if sat else None,
        "conceptos": [{"slug": c["slug"], "titulo": c["title"], "resumen": c["short"]} for c in cards],
        "capas": [{"id": k, "nombre": v} for k, v in MAP_LAYERS.items()],
        "lecciones_recientes": recent_lessons,
    }


def explain(day, run, detections, chart_paths, dwd, sat, recent_lessons) -> dict:
    wd = work_dir(day)
    (wd / "hechos.json").write_text(
        json.dumps(facts(day, run, detections, dwd, sat, recent_lessons), ensure_ascii=False, indent=1),
        encoding="utf-8")
    for p in chart_paths.values():
        shutil.copy(p, wd / p.name)
    if dwd:
        img = Image.open(dwd["path"]).convert("RGB")
        img.thumbnail((1800, 1800))
        img.save(wd / "analisis_dwd.jpg", quality=85)
    if sat:
        shutil.copy(sat["path"], wd / "satelite.png")

    cmd = [_claude_exe(), "-p",
           "--model", config.CLAUDE_MODEL,
           "--system-prompt-file", str(config.PROMPTS / "system.md"),
           "--setting-sources", "",
           "--strict-mcp-config",
           "--tools", "Read", "--allowedTools", "Read",
           "--disable-slash-commands",
           "--no-session-persistence",
           "--output-format", "json",
           "--json-schema", json.dumps(SCHEMA)]
    prompt = (f"Hoy es {day:%d/%m/%Y}. Lee hechos.json y las imágenes de este directorio y escribe la "
              "explicación del día siguiendo tus instrucciones.")
    log.info("Calling claude -p in %s", wd)
    proc = subprocess.run(cmd, input=prompt, cwd=wd, capture_output=True, text=True,
                          encoding="utf-8", timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed ({proc.returncode}): {proc.stderr[-2000:] or proc.stdout[-2000:]}")
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude -p error: {envelope.get('result')}")
    out = envelope.get("structured_output")
    if out is None:
        text = envelope["result"].strip().removeprefix("```json").removesuffix("```")
        out = json.loads(text)
    out["_meta"] = {"model": envelope.get("modelUsage") and list(envelope["modelUsage"]) or config.CLAUDE_MODEL,
                    "duration_s": round(envelope.get("duration_ms", 0) / 1000),
                    "turns": envelope.get("num_turns"),
                    "reference_cost_usd": envelope.get("total_cost_usd")}
    unknown = {m.group(1) for k in ("europa", "foco") for m in LINK_RE.finditer(out[k])} - \
              {c["slug"] for c in load_cards()}
    if unknown:
        log.warning("Explanation used unknown concept slugs (shown as plain text): %s", sorted(unknown))
    return out
