"""Static site: one page per day (text + interactive map), the concept cards and an archive.

Everything works from file:// as well as from a web server: data goes in <script> files that set
globals (no fetch), and the model images are data: URIs so WebGL can use them as textures.
"""
import datetime as dt
import html
import json
import shutil

from PIL import Image

from . import config
from .concepts import load_cards, load_intro, render
from .logo import LOGO_SVG, favicon_link

ACCENT, ACCENT_DARK = "#2a7ab8", "#7bbcf0"  # cielo
FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700"
         "&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap")
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre"]
LEVELS = {"basico": "básico", "intermedio": "intermedio", "avanzado": "avanzado"}
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def long_date(d):
    return f"{DAYS[d.weekday()]} {d.day} de {MONTHS[d.month - 1]} de {d.year}"


def num(x, dec=0):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _head(title, root, extra=""):
    css = (config.ROOT / "aulameteo" / "common.css").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{favicon_link(ACCENT, ACCENT_DARK)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<style>
{css}
:root{{--accent:{ACCENT};--accent-dark:{ACCENT_DARK}}}
</style>
<link rel="stylesheet" href="{root}assets/app.css">
{extra}
</head>
"""


def _header(root, lede, figures=""):
    return f"""<header class="site-header">
  <h1><a href="{root}index.html" class="home">{LOGO_SVG}Aula <span>Meteo</span></a></h1>
  <p class="lede">{lede}</p>
  {figures}
  <nav class="topnav label"><a href="{root}index.html">Hoy</a><a href="{root}conceptos.html">Conceptos</a><a href="{root}archivo.html">Archivo</a></nav>
</header>
"""


def _footer():
    return """<footer class="site-footer">
  <p>Fuentes: modelo IFS del <a href="https://www.ecmwf.int/en/forecasts/datasets/open-data">ECMWF</a>
  (datos abiertos, CC BY 4.0; «Contains modified ECMWF data»), imágenes Meteosat de
  <a href="https://view.eumetsat.int/">EUMETSAT</a> (© EUMETSAT), carta de análisis del
  <a href="https://opendata.dwd.de/weather/charts/analysis/">Deutscher Wetterdienst</a> (CC BY 4.0),
  cartografía <a href="https://www.naturalearthdata.com/">Natural Earth</a> (dominio público) y mapa con
  <a href="https://maplibre.org/">MapLibre GL</a>. Texto redactado cada día por Claude (Anthropic) a partir
  de esos datos: es una explicación didáctica, no una predicción oficial ni un aviso. Para avisos, consulta
  <a href="https://www.aemet.es/es/eltiempo/prediccion/avisos">AEMET</a>.</p>
</footer>
"""


# ---------------------------------------------------------------------------------------------
# Shared assets


def write_assets(history):
    assets = config.SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name in ("app.js", "app.css", "basemap.js"):
        shutil.copy(config.WEB / name, assets / name)
    for name in ("maplibre-gl.js", "maplibre-gl.css"):
        shutil.copy(config.WEB / "vendor" / name, assets / name)
    cards = load_cards()
    titles = {c["slug"]: c["title"] for c in cards}
    data = {c["slug"]: {"title": c["title"], "short": c["short"], "level": c.get("level"),
                        "related": c.get("related", []), "layers": c.get("layers", []),
                        "html": render(c["body"], titles, "../../")}
            for c in cards}
    (assets / "concepts.js").write_text(
        "window.CONCEPTS = " + json.dumps(data, ensure_ascii=False) + ";\n"
        "window.HISTORY = " + json.dumps(history, ensure_ascii=False) + ";\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Day page


def _figures(detections, run):
    by = {d["step_h"]: d for d in detections}
    lows = [f for d in detections for f in d["features"] if f["kind"] == "borrasca"]
    deepest = min(lows, key=lambda f: f["hpa"]) if lows else None
    jets = [f for d in detections for f in d["features"] if f["kind"] == "chorro"]
    rain = [f for d in detections for f in d["features"] if f["kind"] == "lluvia-intensa"]
    focus = by[24]["focus"] if 24 in by else detections[0]["focus"]
    items = []
    if deepest:
        items.append((f"{num(deepest['hpa'])} hPa", "borrasca más profunda (0–72 h)"))
    if jets:
        items.append((f"{num(max(j['max_kmh'] for j in jets))} km/h", "chorro más fuerte"))
    if rain:
        items.append((f"{num(max(r['max_mm'] for r in rain))} mm", "lluvia máx. en 12 h"))
    items.append((f"{num(focus['t850_c']['mean'], 1)} °C", "T 850 hPa en el foco, +24 h"))
    cells = "".join(f"<div><b>{v}</b><span>{k}</span></div>" for v, k in items)
    return f'<div class="figures">{cells}</div>'


def _markers(detections):
    """Per step, the features the map draws (smaller than the full detection records)."""
    keep = ("kind", "concept", "lat", "lon", "where", "hpa", "dam", "max_kmh", "max_mm", "max_jkg")
    return {d["step_h"]: [{k: f[k] for k in keep if k in f} for f in d["features"]] for d in detections}


def _quiz(questions, titles, root):
    """«Ponte a prueba»: the AI's multiple-choice questions; answers are checked in the browser."""
    items = []
    for q in questions:
        opts = q.get("opciones") or []
        if not 0 <= q.get("correcta", -1) < len(opts):
            continue
        buttons = "".join(f'<button type="button">{html.escape(o)}</button>' for o in opts)
        items.append(f'''<li class="q" data-correct="{q["correcta"]}"><p>{html.escape(q["pregunta"])}</p>
        <div class="opts">{buttons}</div><div class="why" hidden>{render(q["explicacion"], titles, root)}</div></li>''')
    if not items:
        return ""
    return f'''<section class="quiz card" id="quiz">
      <h3 class="label">Ponte a prueba</h3>
      <p class="note">{len(items)} preguntas sobre el tiempo de hoy. Puedes mirar el mapa antes de contestar.</p>
      <ol>{"".join(items)}</ol>
      <p class="score" aria-live="polite"></p>
    </section>'''


def _default_step(run, generated):
    hours = (generated - run).total_seconds() / 3600
    return int(min(config.STEPS, key=lambda s: abs(s - hours)))


def _method():
    return """<section class="method" id="metodo">
  <h2>Cómo se hace</h2>
  <ol>
    <li><b>Datos del modelo.</b> Cada mañana se descarga la pasada de las 00 UTC del modelo IFS del ECMWF,
    con resolución de 0,25° (unos 28 km), para Europa y el Atlántico (25–75° N, 45° O–50° E): presión al
    nivel del mar, temperatura a 2 m y a 850 hPa, geopotencial de 500 hPa, viento a 10 m y a 250 hPa,
    precipitación y CAPE, en siete pasos de +0 a +72 h.</li>
    <li><b>Detección de sistemas.</b> Un programa busca los protagonistas del mapa con reglas sencillas
    (tabla de abajo). Cada sistema detectado queda unido a la ficha que lo explica.</li>
    <li><b>Imágenes reales.</b> Se añaden la última carta de análisis del DWD, dibujada por meteorólogos
    con los frentes, y una imagen infrarroja de Meteosat. En el mapa, las capas de satélite (infrarrojo,
    vapor de agua y color) se piden en directo al servidor de EUMETSAT al abrir la página.</li>
    <li><b>Explicación.</b> Claude lee los sistemas detectados, los mapas del modelo, la carta y la imagen de
    satélite, y redacta el texto del día con enlaces a las fichas y al mapa. Las cifras salen del paso 2;
    si algo del texto no cuadra con el mapa, manda el mapa.</li>
  </ol>
  <table class="params">
    <tr><th>Sistema</th><th>Regla</th></tr>
    <tr><td>Borrasca (B) / anticiclón (A)</td><td>Mínimo / máximo de presión en un entorno de unos 500 km,
      al menos 4 / 3 hPa por debajo / encima del anillo que lo rodea; se muestran las 7 / 5 más marcadas.</td></tr>
    <tr><td>Baja fría en altura y DANA</td><td>Mínimo de geopotencial de 500 hPa rodeado por una isohipsa
      cerrada (4 dam por encima). Es DANA si al sur no sopla viento del oeste en 250 hPa (&lt; 5 m/s) y está al
      sur de 55° N.</td></tr>
    <tr><td>Bloqueo</td><td>Alta cerrada en 500 hPa al norte de 45° N con una baja cerrada a su sur.</td></tr>
    <tr><td>Vaguada / dorsal</td><td>Zonas de máxima curvatura del geopotencial de 500 hPa suavizado
      (el 3 % más curvado).</td></tr>
    <tr><td>Corriente en chorro</td><td>Núcleos con viento en 250 hPa de al menos 50 m/s (180 km/h).</td></tr>
    <tr><td>Inestabilidad</td><td>CAPE de al menos 1.000 J/kg en un área amplia.</td></tr>
    <tr><td>Lluvia intensa</td><td>Al menos 20 mm en 12 h en un área amplia.</td></tr>
  </table>
  <p class="note">Límites: el modelo tiene una resolución de unos 28 km y no ve tormentas concretas ni el
  efecto fino del relieve. Los frentes no se calculan: se ven en la carta del DWD. A +72 h la predicción puede
  cambiar bastante de un día a otro.</p>
</section>
"""


def _page_day(day, run, detections, layers_data, text, dwd, sat_time, generated, titles, days_list):
    root = "../../"
    europa = render(text["europa"], titles, root)
    foco = render(text["foco"], titles, root)
    lesson = text["leccion"]
    lesson_slug = lesson["concepto"] if lesson["concepto"] in titles else None
    leccion = render(lesson["texto"], titles, root)
    idx = days_list.index(day) if day in days_list else -1
    prev_day = days_list[idx + 1] if 0 <= idx < len(days_list) - 1 else None
    next_day = days_list[idx - 1] if idx > 0 else None
    nav = '<nav class="daynav label">'
    nav += f'<a href="../{prev_day}/index.html">← {prev_day:%d/%m}</a>' if prev_day else "<span></span>"
    nav += f'<a href="../{next_day}/index.html">{next_day:%d/%m} →</a>' if next_day else "<span></span>"
    nav += "</nav>"
    dwd_block = ""
    if dwd:
        dwd_block = f"""<section class="chart card" id="carta">
    <h2 class="label">La carta oficial</h2>
    <p>Análisis de superficie del servicio meteorológico alemán (DWD) válido el {dwd['valid']:%d/%m/%Y a las %H} UTC,
    dibujado por meteorólogos a partir de observaciones. Aquí sí hay frentes: azul con triángulos, frío; rojo con
    semicírculos, cálido; morado, ocluido. Las borrascas son <b>T</b> y los anticiclones <b>H</b>.
    <a class="concept" href="{root}conceptos.html#carta-de-analisis" data-concept="carta-de-analisis">Cómo leer esta carta</a>.</p>
    <a href="dwd_analysis.jpg" target="_blank" rel="noopener"><img src="dwd_analysis.jpg" alt="Carta de análisis de superficie del DWD con isobaras y frentes sobre el Atlántico norte y Europa" loading="lazy"></a>
  </section>"""
    lede = (f"Una clase diaria de meteorología con los mapas reales de hoy. "
            f"{long_date(day).capitalize()}, pasada del modelo de las {run:%H} UTC del {run:%d/%m}.")
    payload = {
        "date": day.isoformat(), "run": run.strftime("%Y-%m-%dT%H:%MZ"),
        "generated": generated.strftime("%Y-%m-%dT%H:%MZ"),
        "satTime": sat_time.strftime("%Y-%m-%dT%H:%M:00Z"),
        "defaultStep": _default_step(run, generated),
        "focus": config.FOCUS,
        "layers": layers_data, "markers": _markers(detections),
    }
    out = config.SITE / "days" / day.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.js").write_text("window.DAY = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
                                 + ";\n", encoding="utf-8")
    lesson_title = f"Lección del día: {html.escape(titles[lesson_slug])}" if lesson_slug else "Lección del día"
    quiz = _quiz(text.get("preguntas") or [], titles, root)
    page = _head(f"Aula Meteo · {day:%d/%m/%Y}", root,
                 f'<link rel="stylesheet" href="{root}assets/maplibre-gl.css">') + f"""<body class="day">
{_header(root, lede, _figures(detections, run))}
<main class="daygrid">
  <article class="story">
    {nav}
    <h2 class="headline">{html.escape(text['titular'])}</h2>
    <p class="standfirst">{html.escape(text['entradilla'])}</p>
    <h3 class="label">Europa y el Atlántico</h3>
    {europa}
    <h3 class="label">En {html.escape(config.FOCUS['name'])}</h3>
    {foco}
    <section class="lesson card">
      <h3 class="label">{lesson_title}</h3>
      {leccion}
    </section>
    {quiz}
    {dwd_block}
  </article>
  <section class="mapcol" aria-label="Mapa interactivo">
    <div class="mapbox">
      <div id="map" role="application" aria-label="Mapa meteorológico de Europa"></div>
      <div id="tour" class="tour" hidden aria-live="polite"></div>
      <div class="timebar">
        <button type="button" id="play" class="label" aria-label="Animar">▶</button>
        <input type="range" id="step" min="0" max="72" step="12" aria-label="Hora de validez">
        <output id="steplabel" class="data"></output>
      </div>
    </div>
    <div class="controls">
      <p class="tourline"><button type="button" id="tourbtn" class="label">Cómo leer el mapa de hoy</button></p>
      <fieldset id="layers"><legend class="label">Capas</legend></fieldset>
      <div id="legends"></div>
      <p class="note" id="mapnote"></p>
    </div>
  </section>
</main>
{_method()}
{_footer()}
<aside id="drawer" class="drawer" aria-hidden="true" aria-labelledby="drawer-title">
  <button type="button" class="close" aria-label="Cerrar ficha">×</button>
  <div class="drawer-body"></div>
</aside>
<script src="{root}assets/maplibre-gl.js"></script>
<script src="{root}assets/basemap.js"></script>
<script src="{root}assets/concepts.js"></script>
<script src="data.js"></script>
<script src="{root}assets/app.js"></script>
</body>
</html>
"""
    (out / "index.html").write_text(page, encoding="utf-8")
    if dwd:
        img = Image.open(dwd["path"]).convert("RGB")
        img.thumbnail((2200, 2200))
        img.save(out / "dwd_analysis.jpg", quality=82, optimize=True)


# ---------------------------------------------------------------------------------------------
# Concepts, archive, index


def _page_concepts(history):
    cards = load_cards()
    titles = {c["slug"]: c["title"] for c in cards}
    _, intro = load_intro()
    toc = "".join(f'<li><a href="#{c["slug"]}">{html.escape(c["title"])}</a> <span class="note">{html.escape(c["short"])}</span></li>'
                  for c in cards)
    body = ""
    for c in cards:
        seen = history.get(c["slug"], [])[:12]
        seen_html = ""
        if seen:
            links = ", ".join(f'<a href="days/{d}/index.html">{dt.date.fromisoformat(d):%d/%m}</a>' for d in seen)
            seen_html = f'<p class="note">Aparece en: {links}.</p>'
        related = ", ".join(f'<a href="#{r}">{html.escape(titles[r])}</a>' for r in c.get("related", []) if r in titles)
        body += f"""<article class="card concept-card" id="{c['slug']}">
  <p class="badge">{LEVELS.get(c.get('level'), c.get('level', ''))}</p>
  <h2>{html.escape(c['title'])}</h2>
  <p class="short">{html.escape(c['short'])}</p>
  {render(c['body'], titles, '', anchors=True)}
  {f'<p class="note">Relacionadas: {related}.</p>' if related else ''}
  {seen_html}
</article>
"""
    page = _head("Aula Meteo · Conceptos", "") + f"""<body class="concepts">
{_header('', 'Las fichas de conceptos: qué es cada cosa, cómo se ve en el mapa, qué tiempo trae y un truco para reconocerla.')}
<main class="prose">
  <section class="intro">{render(intro, titles, '', anchors=True)}</section>
  <h2 class="label">Todas las fichas</h2>
  <ol class="toc">{toc}</ol>
  {body}
</main>
{_footer()}
</body>
</html>
"""
    (config.SITE / "conceptos.html").write_text(page, encoding="utf-8")


def _page_archive(entries):
    rows = "".join(
        f'<li><a href="days/{e["date"]}/index.html"><span class="data">{dt.date.fromisoformat(e["date"]):%d/%m/%Y}</span> '
        f'{html.escape(e["titular"])}</a> <span class="note">{html.escape(e.get("lesson_title") or "")}</span></li>'
        for e in entries)
    page = _head("Aula Meteo · Archivo", "") + f"""<body class="archive">
{_header('', 'Todos los días explicados, del más reciente al más antiguo.')}
<main class="prose"><ol class="archive-list">{rows}</ol></main>
{_footer()}
</body>
</html>
"""
    (config.SITE / "archivo.html").write_text(page, encoding="utf-8")


def _page_index(latest):
    target = f"days/{latest}/index.html"
    (config.SITE / "index.html").write_text(
        f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={target}"><title>Aula Meteo</title></head>'
        f'<body><p><a href="{target}">Ir al día de hoy</a></p></body></html>\n', encoding="utf-8")


def build_day(day, run, detections, layers_data, text, dwd, sat_time, generated):
    """Write today's page and refresh the shared pages (concepts, archive, index)."""
    history, entries = _history()
    titles = {c["slug"]: c["title"] for c in load_cards()}
    days_list = sorted({dt.date.fromisoformat(e["date"]) for e in entries} | {day}, reverse=True)
    write_assets(history)
    _page_day(day, run, detections, layers_data, text, dwd, sat_time, generated, titles, days_list)
    rebuild_shared()


def rebuild_shared():
    history, entries = _history()
    write_assets(history)
    _page_concepts(history)
    _page_archive(entries)
    if entries:
        _page_index(entries[0]["date"])


def _history():
    """Concept -> days it appeared in, and the archive entries, from data/days/*/explain.json."""
    titles = {c["slug"]: c["title"] for c in load_cards()}
    history, entries = {}, []
    root = config.DATA / "days"
    for d in sorted(root.glob("*/explain.json"), reverse=True) if root.exists() else []:
        text = json.loads(d.read_text(encoding="utf-8"))
        date = d.parent.name
        if not (config.SITE / "days" / date / "index.html").exists():
            continue
        lesson = text.get("leccion", {}).get("concepto")
        entries.append({"date": date, "titular": text["titular"],
                        "lesson_title": f"Lección: {titles[lesson]}" if lesson in titles else None})
        for slug in sorted(set(text.get("conceptos", [])) & set(titles)):
            history.setdefault(slug, []).append(date)
    return history, entries
