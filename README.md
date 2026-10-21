# Aula Meteo

Una clase diaria de meteorología con los mapas reales del día. Cada mañana descarga el modelo del
ECMWF para Europa y el Atlántico, detecta las borrascas, anticiclones, DANA, vaguadas y el chorro, y
genera una página con un mapa interactivo, una explicación escrita por Claude y enlaces a fichas de
conceptos. Se genera en local y se publica en <https://asensio94.github.io/aula-meteo/>.

> **Estado: activo.** Se actualiza solo y sigue en desarrollo.

## Cómo funciona

1. **Descarga** (`fetch.py`): la pasada de las 00 UTC del modelo IFS del ECMWF (0,25°, datos abiertos)
   en siete pasos de +0 a +72 h: presión, temperatura a 2 m y 850 hPa, geopotencial de 500 hPa,
   viento a 10 m y a 250 hPa, precipitación y CAPE (unos 83 MB al día). También la última carta de
   análisis del DWD (con frentes) y una imagen infrarroja de Meteosat (EUMETSAT, con reintentos: el
   servidor responde 503 a veces).
2. **Campos** (`fields.py`): recorta al dominio 25–75° N, 45° O–50° E y pasa a unidades cómodas (hPa,
   °C, dam, mm en 12 h).
3. **Detección** (`detect.py`): reglas sencillas y a la vista (tabla en la sección «Cómo se hace» de
   cada página). Cada sistema queda unido a la ficha que lo explica.
4. **Capas** (`layers.py`): isobaras e isohipsas como GeoJSON, campos de color como PNG
   reproyectados a Mercator y el viento a 10 m como rejilla de 1° (velocidad y dirección), todo
   incrustado en la página.
5. **Explicación** (`explain.py`): llama a Claude Code en modo no interactivo (`claude -p`) con la
   suscripción del usuario, aislado de su configuración (prompt propio en `prompts/system.md`, sin
   ajustes, sin MCP, solo la herramienta Read, en un directorio de trabajo fuera de este árbol). Lee los
   sistemas detectados, dos láminas del modelo (`quicklook.py`), la carta del DWD y el satélite, y
   devuelve JSON: titular, Europa, región foco, lección del día, tres preguntas de «Ponte a prueba» y
   conceptos usados.
6. **Web** (`site.py`, `web/app.js`): una página por día con el mapa (MapLibre), deslizador de
   tiempo, capas (flechas de viento que se densifican al acercarse; satélite en vivo en infrarrojo,
   vapor de agua o color), cajón de fichas, enlaces «mira aquí» que mueven el mapa, una guía «Cómo leer
   el mapa de hoy» montada sin IA a partir de los sistemas detectados y las preguntas, que se corrigen
   en el navegador; además la página de conceptos y el archivo. Funciona abriendo los HTML desde disco.
7. **Publicación** (`publish.py`): sube `site/` a la rama `gh-pages` como un único commit sin
   historial, reescrito cada día (cada página lleva unos 2 MB de datos del mapa; con historial el repo
   crecería unos 700 MB al año). La web guarda los últimos 180 días; los textos se quedan en `data/`.
   No hay GitHub Actions: la explicación sale de la suscripción de Claude del ordenador que la genera.

## Contraste / validación

Pendiente de forma sistemática (comparar la detección con la carta del DWD día a día). Revisado a
mano el 20/10/2026: el texto generado usa las cifras de la detección (979 hPa, 89 mm en 12 h en el
Atlántico, 71,5 mm en el foco…) y no inventa otras. Se le pasa el foco en todos los pasos de 12 h
para que no se pierda la lluvia que cae entre los pasos principales.

## Límites

- El modelo tiene unos 28 km de resolución: no ve tormentas concretas ni el efecto fino del relieve.
- Los frentes no se calculan; se ven en la carta del DWD, que no se puede superponer al mapa
  (proyección estereográfica).
- La detección es deliberadamente simple: puede marcar vaguadas débiles o perder sistemas pequeños.
- El texto lo redacta un modelo de lenguaje: es didáctico, no una predicción oficial ni un aviso.
- Depende de que el ordenador esté encendido a la hora de la tarea y con sesión iniciada en Claude Code.

## Pendiente

- Radar y avisos de AEMET para la región foco (necesita una clave gratuita de AEMET OpenData).
- La composición de niebla de EUMETSAT (`mtg_fd:rgb_fog`) como cuarto canal de satélite.
- Rachas de viento (`10fg` del ECMWF) además del viento medio.

## Uso

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m aulameteo.basemap          # una vez: costas y fronteras (Natural Earth)
.\register_task.ps1                                # una vez: tarea diaria a las 11:00
.\run_daily.ps1                                    # el día de hoy (y lo publica)
.\run_daily.ps1 --reuse-text                       # rehacer la página sin volver a llamar a Claude (misma carta del DWD)
.\run_daily.ps1 --rebuild-site                     # solo fichas y archivo (tras editar concepts/)
```

`run_daily.ps1` siempre publica; para probar sin publicar, `.venv\Scripts\python -m aulameteo.daily`
con las mismas opciones. La región foco y el modelo de Claude se cambian en `aulameteo/config.py`. Las fichas son Markdown
en `concepts/`; en el texto, `[[slug|palabra]]` enlaza una ficha y `[mira aquí](#ver:LAT,LON,ZOOM,CAPAS,PASO)`
mueve el mapa.

### Datos que se guardan

| Fichero | Contenido |
|---|---|
| `data/grib/AAAAMMDD/` | GRIB del modelo (se guardan los dos últimos días) |
| `data/days/AAAA-MM-DD/detections.json` | Sistemas detectados por paso |
| `data/days/AAAA-MM-DD/explain.json` | Texto generado y metadatos de la llamada |
| `data/days/AAAA-MM-DD/*.png` | Láminas del modelo, carta del DWD y satélite que vio Claude |
| `data/logs/AAAA-MM.log` | Registro de cada ejecución |
| `site/` | La web generada (últimos 180 días); se publica en la rama `gh-pages` |

### Fuentes y licencias

ECMWF Open Data (CC BY 4.0), EUMETSAT (© EUMETSAT, uso según su política de datos), Deutscher
Wetterdienst (CC BY 4.0), Natural Earth (dominio público), MapLibre GL JS (BSD-3). Código con
licencia MIT; textos y fichas propios con CC BY 4.0.
