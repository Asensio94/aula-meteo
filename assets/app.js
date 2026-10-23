/* Aula Meteo — interactive map, time slider, "mira aquí" links and the concept drawer.
   Data comes from globals set by <script> files: DAY (data.js), CONCEPTS/HISTORY (concepts.js),
   BASEMAP (basemap.js). No fetch, so the page also works when opened from disk. */
(function () {
  "use strict";

  const LAYERS = [
    { id: "msl", name: "Presión en superficie", kind: "contour", concept: "presion-atmosferica" },
    { id: "z500", name: "Geopotencial 500 hPa", kind: "contour", concept: "geopotencial-500" },
    { id: "t850", name: "Temperatura 850 hPa", kind: "image", concept: "masas-de-aire" },
    { id: "precip", name: "Precipitación 12 h", kind: "image", concept: "precipitacion" },
    { id: "cape", name: "CAPE (energía para tormentas)", kind: "image", concept: "inestabilidad-y-cape" },
    { id: "jet250", name: "Viento 250 hPa (chorro)", kind: "image", concept: "corriente-en-chorro" },
    { id: "wind10", name: "Viento a 10 m", kind: "wind", concept: "viento-y-presion" },
    { id: "sat", name: "Satélite infrarrojo", kind: "sat", concept: "satelite" },
    { id: "satwv", name: "Satélite vapor de agua", kind: "sat", concept: "vapor-de-agua" },
    { id: "satgeo", name: "Satélite color (GeoColour)", kind: "sat", concept: "satelite" },
  ];
  // EUMETSAT View layers: how often a new image comes out and how long after its time it is served.
  // Only one satellite channel is shown at a time.
  const SAT = {
    sat: { layer: "mtg_fd:ir105_hrfi", every: 10, lag: 40, name: "Satélite infrarrojo (MTG)",
      hint: "Blanco brillante: nubes altas y frías; gris: nubes bajas o suelo templado." },
    satwv: { layer: "msg_fes:wv062", every: 15, lag: 40, name: "Satélite vapor de agua (Meteosat)",
      hint: "Claro: aire húmedo en capas medias y altas. Oscuro: aire seco que baja, a menudo detrás de una borrasca." },
    satgeo: { layer: "mtg_fd:rgb_geocolour", every: 10, lag: 75, name: "Satélite color (MTG GeoColour)",
      hint: "De día, como una foto en color. De noche mezcla las nubes del infrarrojo con las luces de las ciudades." },
  };
  const WIND = [  // km/h -> colour, from calm to storm force
    [0, "#64748b"], [20, "#0f766e"], [40, "#ca8a04"], [60, "#ea580c"], [80, "#b91c1c"], [100, "#6b21a8"],
  ];
  const IMAGES = ["t850", "cape", "precip", "jet250"];  // drawn in this order; the satellite goes on top
  const KINDS = {
    borrasca: { name: "Borrasca", label: "B", layer: "msl", color: "#c81e1e", size: 24 },
    anticiclon: { name: "Anticiclón", label: "A", layer: "msl", color: "#1d4ed8", size: 24 },
    dana: { name: "DANA", label: "DANA", layer: "z500", color: "#9a3412", size: 15 },
    "baja-fria-en-altura": { name: "Baja fría en altura", label: "B", layer: "z500", color: "#9a3412", size: 18 },
    bloqueo: { name: "Bloqueo", label: "BLOQUEO", layer: "z500", color: "#9a3412", size: 14 },
    "alta-en-altura": { name: "Alta en altura", label: "A", layer: "z500", color: "#9a3412", size: 18 },
    vaguada: { name: "Vaguada", label: "vaguada", layer: "z500", color: "#9a3412", size: 13 },
    dorsal: { name: "Dorsal", label: "dorsal", layer: "z500", color: "#9a3412", size: 13 },
    chorro: { name: "Núcleo del chorro", label: "chorro", layer: "jet250", color: "#4c1d95", size: 13 },
    inestabilidad: { name: "Inestabilidad", label: "CAPE", layer: "cape", color: "#9d0208", size: 13 },
    "lluvia-intensa": { name: "Lluvia intensa", label: "lluvia", layer: "precip", color: "#1e3a8a", size: 13 },
  };
  const WMS = "https://view.eumetsat.int/geoserver/wms?service=WMS&version=1.3.0&request=GetMap" +
    "&styles=&crs=EPSG:3857&bbox={bbox-epsg-3857}&width=256&height=256&format=image/png&transparent=true";
  const DAYS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  const STORE = "aulameteo.layers";
  const LEVELS = { basico: "básico", intermedio: "intermedio", avanzado: "avanzado" };

  const run = new Date(DAY.run);
  const steps = DAY.layers.steps.map((s) => s.step_h);
  const state = { step: DAY.defaultStep, layers: new Set(loadLayers()) };
  const shown = {};  // source id -> image URL currently loaded, to avoid needless (aborting) reloads
  const initialView = parseView(location.hash);
  if (initialView) applyView(initialView);

  function loadLayers() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE));
      if (Array.isArray(saved) && saved.length) return saved;
    } catch (e) { /* private mode or blocked storage */ }
    return ["msl", "precip"];
  }
  function onlyOneSat(set, keep) {  // the satellite channels are alternatives, not overlays
    const ids = Object.keys(SAT);
    keep = keep || ids.find((id) => set.has(id));
    for (const id of ids) if (id !== keep && set.has(id)) set.delete(id);
  }
  function saveLayers() {
    try { localStorage.setItem(STORE, JSON.stringify([...state.layers])); } catch (e) { /* ignore */ }
  }

  const fmtNum = (x) => Number(x).toLocaleString("es-ES");
  const validAt = (h) => new Date(run.getTime() + h * 3600e3);
  const pad = (n) => String(n).padStart(2, "0");
  const fmtTime = (d) => `${DAYS[d.getUTCDay()]} ${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  const stepData = (h) => DAY.layers.steps.find((s) => s.step_h === h);

  /* ------------------------------------------------------------------ map */

  const map = new maplibregl.Map({
    container: "map",
    center: [5, 48],
    zoom: 2.9,
    minZoom: 2,
    maxZoom: 8,
    maxBounds: [[-70, 15], [75, 82]],
    attributionControl: false,
    style: {
      version: 8,
      glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {
        land: { type: "geojson", data: BASEMAP.land },
        coast: { type: "geojson", data: BASEMAP.coast },
        borders: { type: "geojson", data: BASEMAP.borders },
      },
      layers: [
        { id: "bg", type: "background", paint: { "background-color": "#d6e2ea" } },
        { id: "land", type: "fill", source: "land", paint: { "fill-color": "#f2efe8" } },
      ],
    },
  });
  window.aulaMap = map;  // handy from the console
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: "ECMWF IFS (CC BY 4.0) · © EUMETSAT · Natural Earth",
  }));

  function satTime(h, id = "sat") {
    const c = SAT[id];
    const latest = new Date(Date.now() - c.lag * 60e3);
    latest.setUTCMinutes(latest.getUTCMinutes() - (latest.getUTCMinutes() % c.every), 0, 0);
    const want = validAt(h);
    return want < latest ? want : latest;
  }
  const satUrl = (id, d) => `${WMS}&layers=${SAT[id].layer}&time=${d.toISOString().slice(0, 16)}:00Z`;
  const satOn = () => Object.keys(SAT).find((id) => state.layers.has(id));

  /* 10 m wind: one arrow per degree. Each point gets a "tier" (0 every 4°, 1 every 2°, 2 the rest)
     so that zooming in adds arrows instead of cramming them all in at once. */
  function windData(h) {
    const m = DAY.layers.wind, w = stepData(h).wind;
    const feats = [];
    if (!m || !w) return { type: "FeatureCollection", features: feats };
    for (let i = 0; i < m.ny; i++) {
      for (let j = 0; j < m.nx; j++) {
        const k = i * m.nx + j, kmh = w.kmh[k];
        if (kmh < 3) continue;
        const tier = i % 4 === 0 && j % 4 === 0 ? 0 : i % 2 === 0 && j % 2 === 0 ? 1 : 2;
        feats.push({ type: "Feature", geometry: { type: "Point", coordinates: [m.lon0 + j * m.dlon, m.lat0 + i * m.dlat] },
          properties: { kmh, dir: w.dir10[k] * 10, tier } });
      }
    }
    return { type: "FeatureCollection", features: feats };
  }
  function arrowImage() {  // white arrow pointing north, used as an SDF so it can be tinted by speed
    const n = 32, c = document.createElement("canvas");
    c.width = c.height = n;
    const g = c.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(n / 2 - 1.5, 9, 3, 20);
    g.beginPath(); g.moveTo(n / 2, 1); g.lineTo(n / 2 + 7, 13); g.lineTo(n / 2 - 7, 13); g.closePath(); g.fill();
    return g.getImageData(0, 0, n, n);
  }

  map.on("load", () => {
    const s0 = stepData(state.step);
    const b = DAY.layers.bounds;
    for (const id of IMAGES) {
      shown[id] = s0.images[id] || blankPng();
      map.addSource(id, { type: "image", url: shown[id], coordinates: b });
      map.addLayer({ id, type: "raster", source: id, paint: { "raster-opacity": id === "t850" ? 0.8 : 0.85, "raster-fade-duration": 0, "raster-resampling": "linear" }, layout: { visibility: "none" } });
    }
    for (const id of Object.keys(SAT)) {  // sources are created now but only fetch tiles once visible
      shown[id] = satUrl(id, satTime(state.step, id));
      map.addSource(id, { type: "raster", tiles: [shown[id]], tileSize: 256 });
      map.addLayer({ id, type: "raster", source: id, paint: { "raster-opacity": 0.9 }, layout: { visibility: "none" } });
    }
    map.addLayer({ id: "coast", type: "line", source: "coast", paint: { "line-color": "#5b524c", "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.7, 6, 1.4] } });
    map.addLayer({ id: "borders", type: "line", source: "borders", paint: { "line-color": "#8f857e", "line-width": 0.5, "line-dasharray": [2, 2] } });
    const contourStyle = { msl: "#1e293b", z500: "#9a3412" };
    for (const id of ["z500", "msl"]) {
      map.addSource(id, { type: "geojson", data: s0.contours[id] });
      map.addLayer({
        id, type: "line", source: id, layout: { visibility: "none", "line-join": "round" },
        paint: { "line-color": contourStyle[id], "line-width": ["case", ["get", "bold"], id === "z500" ? 2.2 : 1.7, id === "z500" ? 1.2 : 0.8] },
      });
      map.addLayer({
        id: id + "-lab", type: "symbol", source: id,
        layout: {
          visibility: "none", "symbol-placement": "line", "symbol-spacing": 280,
          "text-field": ["to-string", ["get", "v"]], "text-font": ["Open Sans Semibold"], "text-size": 11,
        },
        paint: { "text-color": contourStyle[id], "text-halo-color": "rgba(255,255,255,.9)", "text-halo-width": 1.6 },
      });
    }
    map.addImage("arrow", arrowImage(), { sdf: true });
    map.addSource("wind10", { type: "geojson", data: windData(state.step) });
    const windColour = ["interpolate", ["linear"], ["get", "kmh"], ...WIND.flat()];
    [[0, 0], [1, 4], [2, 5.5]].forEach(([tier, minzoom]) => map.addLayer({
      id: `wind10-${tier}`, type: "symbol", source: "wind10", minzoom, filter: ["==", ["get", "tier"], tier],
      layout: {
        visibility: "none", "icon-image": "arrow", "icon-rotate": ["get", "dir"], "icon-rotation-alignment": "map",
        "icon-allow-overlap": true, "icon-ignore-placement": true,
        "icon-size": ["interpolate", ["linear"], ["get", "kmh"], 0, 0.35, 30, 0.55, 80, 0.8],
      },
      paint: { "icon-color": windColour, "icon-halo-color": "rgba(255,255,255,.85)", "icon-halo-width": 1 },
    }));
    map.addSource("markers", { type: "geojson", data: markers(state.step) });
    map.addLayer({
      id: "markers", type: "symbol", source: "markers",
      layout: {
        "text-field": ["format", ["get", "label"], { "font-scale": 1 }, ["get", "sub"], { "font-scale": 0.55 }],
        "text-font": ["Open Sans Semibold"], "text-size": ["get", "size"],
        "text-line-height": 1.0, "text-padding": 1,
        "symbol-sort-key": ["-", 0, ["get", "size"]],  // B/A win over the smaller labels
      },
      paint: { "text-color": ["get", "color"], "text-halo-color": "rgba(255,255,255,.95)", "text-halo-width": 2 },
    });
    map.on("click", "markers", (e) => popup(e.features[0], e.lngLat));
    map.on("mouseenter", "markers", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "markers", () => (map.getCanvas().style.cursor = ""));
    showTime();
    applyLayers();
    if (initialView) map.jumpTo({ center: [initialView.lon, initialView.lat], zoom: initialView.zoom });
  });

  function blankPng() {
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
  }

  function markers(h) {
    const feats = (DAY.markers[h] || []).map((f, i) => {
      const k = KINDS[f.kind] || { name: f.kind, label: "•", layer: "msl", color: "#333", size: 13 };
      let sub = "";
      if (f.hpa != null) sub = "\n" + Math.round(f.hpa);
      else if (f.max_kmh != null) sub = "\n" + f.max_kmh + " km/h";
      else if (f.max_mm != null) sub = "\n" + f.max_mm + " mm";
      else if (f.max_jkg != null) sub = "\n" + fmtNum(f.max_jkg);
      else if (f.dam != null && ["dana", "baja-fria-en-altura", "alta-en-altura"].includes(f.kind)) sub = "\n" + Math.round(f.dam);
      return {
        type: "Feature", geometry: { type: "Point", coordinates: [f.lon, f.lat] },
        properties: { i, label: k.label, sub, color: k.color, size: k.size, layer: k.layer },
      };
    });
    return { type: "FeatureCollection", features: feats };
  }

  function popup(feature, lngLat) {
    const f = DAY.markers[state.step][feature.properties.i];
    const k = KINDS[f.kind] || { name: f.kind };
    const vals = [];
    if (f.hpa != null) vals.push(`${fmtNum(f.hpa)} hPa en el centro`);
    if (f.dam != null) vals.push(`${fmtNum(f.dam)} dam en 500 hPa`);
    if (f.max_kmh != null) vals.push(`viento máximo de ${fmtNum(f.max_kmh)} km/h a unos 10 km de altura`);
    if (f.max_mm != null) vals.push(`hasta ${fmtNum(f.max_mm)} mm en 12 h`);
    if (f.max_jkg != null) vals.push(`CAPE de hasta ${fmtNum(f.max_jkg)} J/kg`);
    const c = CONCEPTS[f.concept];
    const html = `<b>${k.name}</b> ${f.where}<br>${vals.join("<br>")}` +
      (c ? `<br><a href="#" class="concept" data-concept="${f.concept}">Qué es: ${c.title}</a>` : "");
    new maplibregl.Popup({ maxWidth: "260px" }).setLngLat(lngLat).setHTML(html).addTo(map);
  }

  function applyLayers() {
    if (!map.isStyleLoaded() && !map.getLayer("markers")) return;
    for (const L of LAYERS) {
      const on = state.layers.has(L.id);
      const vis = on ? "visible" : "none";
      if (L.kind === "contour") {
        map.setLayoutProperty(L.id, "visibility", vis);
        map.setLayoutProperty(L.id + "-lab", "visibility", vis);
      } else if (L.kind === "wind") {
        const missing = !stepData(state.step).wind;
        for (const t of [0, 1, 2]) map.setLayoutProperty(`wind10-${t}`, "visibility", on && !missing ? "visible" : "none");
      } else {
        const missing = L.kind === "image" && !stepData(state.step).images[L.id];
        map.setLayoutProperty(L.id, "visibility", on && !missing ? "visible" : "none");
      }
      const box = document.querySelector(`#layers input[value="${L.id}"]`);
      if (box) box.checked = on;
    }
    map.setFilter("markers", ["in", ["get", "layer"], ["literal", [...state.layers]]]);
    // Over the (dark) infrared image, light lines read better, as on classic satellite charts.
    const dark = Boolean(satOn());
    map.setPaintProperty("msl", "line-color", dark ? "#f8fafc" : "#1e293b");
    map.setPaintProperty("msl-lab", "text-color", dark ? "#f8fafc" : "#1e293b");
    map.setPaintProperty("msl-lab", "text-halo-color", dark ? "rgba(0,0,0,.7)" : "rgba(255,255,255,.9)");
    map.setPaintProperty("coast", "line-color", dark ? "#e9c46a" : "#5b524c");
    map.setPaintProperty("borders", "line-color", dark ? "#c9a94f" : "#8f857e");
    renderLegends();
    saveLayers();
  }

  function applyStep() {
    if (!map.getSource("markers")) return;  // map still loading: its load handler will use `state`
    const s = stepData(state.step);
    for (const id of IMAGES) {
      if (s.images[id] && shown[id] !== s.images[id]) {
        shown[id] = s.images[id];
        map.getSource(id).updateImage({ url: shown[id], coordinates: DAY.layers.bounds });
      }
    }
    for (const id of ["msl", "z500"]) map.getSource(id).setData(s.contours[id]);
    map.getSource("markers").setData(markers(state.step));
    for (const id of Object.keys(SAT)) {
      const url = satUrl(id, satTime(state.step, id));
      if (shown[id] !== url) { shown[id] = url; map.getSource(id).setTiles([url]); }
    }
    map.getSource("wind10").setData(windData(state.step));
    showTime();
    applyLayers();
  }

  function showTime() {
    document.getElementById("step").value = state.step;
    document.getElementById("steplabel").textContent = `${fmtTime(validAt(state.step))} (+${state.step} h)`;
  }

  /* ------------------------------------------------------------------ controls */

  function buildControls() {
    const fs = document.getElementById("layers");
    for (const L of LAYERS) {
      const row = document.createElement("label");
      row.className = "layer";
      row.innerHTML = `<input type="checkbox" value="${L.id}"> <span>${L.name}</span>` +
        ` <a href="#" class="concept info" data-concept="${L.concept}" aria-label="Qué es: ${L.name}">?</a>`;
      row.querySelector("input").addEventListener("change", (e) => {
        if (e.target.checked) { onlyOneSat(state.layers, L.id); state.layers.add(L.id); } else state.layers.delete(L.id);
        applyLayers();
      });
      if (L.kind === "wind" && !DAY.layers.wind) row.hidden = true;  // days built before the wind layer existed
      fs.appendChild(row);
    }
    const slider = document.getElementById("step");
    slider.min = steps[0];
    slider.max = steps[steps.length - 1];
    slider.addEventListener("input", () => { state.step = Number(slider.value); applyStep(); });
    let timer = null;
    const play = document.getElementById("play");
    play.addEventListener("click", () => {
      if (timer) { clearInterval(timer); timer = null; play.textContent = "▶"; return; }
      play.textContent = "❚❚";
      timer = setInterval(() => {
        const i = steps.indexOf(state.step);
        state.step = steps[(i + 1) % steps.length];
        applyStep();
      }, 1300);
    });
  }

  function renderLegends() {
    const box = document.getElementById("legends");
    const parts = [];
    for (const L of LAYERS) {
      if (!state.layers.has(L.id)) continue;
      const lg = DAY.layers.legends[L.id];
      if (lg) {
        const cells = lg.colors.map((c, i) => `<span style="background:${c}"></span>`).join("");
        const labels = lg.levels.map((v) => `<span>${fmtNum(v)}</span>`).join("");
        parts.push(`<div class="legend"><div class="label">${lg.name} (${lg.unit})</div><div class="ramp">${cells}</div><div class="ticks">${labels}</div></div>`);
      } else if (L.id === "msl") {
        parts.push(`<div class="legend"><span class="swatch" style="border-color:#1e293b"></span> Isobaras cada 4 hPa; más gruesas cada 20 (1000, 1020…). <b style="color:#c81e1e">B</b> borrasca, <b style="color:#1d4ed8">A</b> anticiclón.</div>`);
      } else if (L.id === "z500") {
        parts.push(`<div class="legend"><span class="swatch" style="border-color:#9a3412"></span> Isohipsas de 500 hPa cada 4 dam (552 = 5520 m); gruesas cada 12.</div>`);
      }
    }
    if (state.layers.has("wind10") && DAY.layers.wind) {
      const sw = WIND.map(([v, c]) => `<span style="color:${c}">➤ ${v}</span>`).join(" ");
      parts.push(`<div class="legend"><div class="label">Viento medio a 10 m (km/h)</div>${sw}+<br>` +
        "La flecha apunta hacia donde va el aire. Las rachas pueden ser bastante más fuertes.</div>");
    }
    const sat = satOn();
    if (sat) {
      const t = satTime(state.step, sat);
      const real = Math.abs(t - validAt(state.step)) < 60e3;
      parts.push(`<div class="legend">${SAT[sat].name}, EUMETSAT: ${fmtTime(t)}. ` +
        (real ? "Es la imagen real de esa hora: compárala con el modelo." : "Esa hora aún no ha llegado; se muestra la última imagen disponible.") +
        ` ${SAT[sat].hint}</div>`);
    }
    box.innerHTML = parts.join("");
  }

  /* ------------------------------------------------------------------ "mira aquí" links */

  function parseView(hash) {
    const m = hash.match(/^#ver:(-?[\d.]+),(-?[\d.]+),([\d.]+),([a-z0-9+]+)(?:,(\d+))?$/);
    if (!m) return null;
    return { lat: Number(m[1]), lon: Number(m[2]), zoom: Number(m[3]),
      ids: m[4].split("+").filter((id) => LAYERS.some((L) => L.id === id)),
      step: m[5] != null && steps.includes(Number(m[5])) ? Number(m[5]) : null };
  }
  function applyView(v) {
    if (v.ids.length) state.layers = new Set(v.ids);
    onlyOneSat(state.layers);
    if (v.step != null) state.step = v.step;
  }

  function goTo(hash) {
    const v = parseView(hash);
    if (!v) return;
    applyView(v);
    applyStep();
    map.flyTo({ center: [v.lon, v.lat], zoom: v.zoom, speed: 1.4 });
    const mapEl = document.querySelector(".mapbox");
    const r = mapEl.getBoundingClientRect();
    if (r.top < 0 || r.bottom > window.innerHeight) mapEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  /* ------------------------------------------------------------------ concept drawer */

  const drawer = document.getElementById("drawer");
  const drawerBody = drawer.querySelector(".drawer-body");
  let lastFocus = null;

  function openConcept(slug) {
    const c = CONCEPTS[slug];
    if (!c) return false;
    const days = (HISTORY[slug] || []).filter((d) => d !== DAY.date).slice(0, 8);
    const related = (c.related || []).filter((r) => CONCEPTS[r])
      .map((r) => `<a href="#" class="concept" data-concept="${r}">${CONCEPTS[r].title}</a>`).join(" · ");
    const layers = (c.layers || []).filter((id) => LAYERS.some((L) => L.id === id));
    drawerBody.innerHTML =
      `<p class="badge">${LEVELS[c.level] || c.level || ""}</p><h2 id="drawer-title">${c.title}</h2><p class="short">${c.short}</p>` +
      (layers.length ? `<p><button type="button" class="showlayers label" data-layers="${layers.join("+")}">Verlo en el mapa de hoy</button></p>` : "") +
      c.html +
      (related ? `<p class="note">Relacionadas: ${related}</p>` : "") +
      (days.length ? `<p class="note">Otros días en que apareció: ${days.map((d) => `<a href="../${d}/index.html">${d.slice(8, 10)}/${d.slice(5, 7)}</a>`).join(", ")}</p>` : "") +
      `<p class="note"><a href="../../conceptos.html#${slug}">Abrir la ficha en su página</a></p>`;
    drawerBody.scrollTop = 0;
    if (!drawer.classList.contains("open")) lastFocus = document.activeElement;
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    drawer.querySelector(".close").focus();
    return true;
  }
  function closeDrawer() {
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    if (lastFocus) lastFocus.focus();
  }
  drawer.querySelector(".close").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a, button.showlayers");
    if (!a) return;
    if (a.matches("button.showlayers")) {
      state.layers = new Set(a.dataset.layers.split("+"));
      onlyOneSat(state.layers);
      applyLayers();
      if (window.innerWidth < 900) closeDrawer();
      document.querySelector(".mapbox").scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (a.dataset.concept && openConcept(a.dataset.concept)) { e.preventDefault(); return; }
    const href = a.getAttribute("href") || "";
    if (href.startsWith("#ver:")) { e.preventDefault(); goTo(href); }
  });

  window.addEventListener("hashchange", () => goTo(location.hash));

  /* ------------------------------------------------------------------ guided tour */

  // Built from today's detections: each stop shows one way of reading the map, on today's best example.
  // Where the tour looks first: the systems that reach the focus region, not the Urals or Arabia.
  const NEAR = { lat: [30, 62], lon: [-35, 25] };
  const near = (f) => f.lat >= NEAR.lat[0] && f.lat <= NEAR.lat[1] && f.lon >= NEAR.lon[0] && f.lon <= NEAR.lon[1];
  function extreme(kind, key, lowest = false) {  // the strongest example of a kind over the 72 h, near first
    for (const inside of [near, () => true]) {
      let best = null;
      for (const h of steps) {
        for (const f of DAY.markers[h] || []) {
          if (f.kind !== kind || f[key] == null || !inside(f)) continue;
          if (!best || (lowest ? f[key] < best.f[key] : f[key] > best.f[key])) best = { f, h };
        }
      }
      if (best) return best;
    }
    return null;
  }
  function tourStops() {
    const wind = DAY.layers.wind ? "+wind10" : "";
    const when = (h) => fmtTime(validAt(h)).replace(/ \d\d:\d\d UTC$/, (m) => ` a las${m}`);
    const stops = [];
    const low = extreme("borrasca", "hpa", true);
    if (low) stops.push({ f: low.f, h: low.h, zoom: 4, ids: "msl" + wind, concept: "borrasca",
      html: `<b>Presión en superficie.</b> Las líneas son isobaras: unen puntos con la misma presión, cada 4 hPa. ` +
        `La B que está ${low.f.where} es la borrasca más profunda de nuestro lado del mapa: ${fmtNum(low.f.hpa)} hPa el ${when(low.h)}. ` +
        (wind ? "Donde las isobaras se aprietan, el viento sopla más fuerte: mira las flechas, que giran al revés que las agujas del reloj." :
          "Donde las isobaras se aprietan, el viento sopla más fuerte.") });
    const high = extreme("anticiclon", "hpa");
    if (high) stops.push({ f: high.f, h: high.h, zoom: 4, ids: "msl" + wind, concept: "anticiclon",
      html: `La A que está ${high.f.where} es un anticiclón de ${fmtNum(high.f.hpa)} hPa. Isobaras separadas: ` +
        "viento flojo y, casi siempre, tiempo estable. Alrededor de una A el aire gira en el sentido de las agujas del reloj." });
    const jet = extreme("chorro", "max_kmh");
    if (jet) stops.push({ f: jet.f, h: jet.h, zoom: 3, ids: "jet250+z500", concept: "corriente-en-chorro",
      html: `<b>A unos 10 km de altura.</b> La mancha morada es la corriente en chorro. Su núcleo más fuerte, ` +
        `${jet.f.where}, sopla a ${fmtNum(jet.f.max_kmh)} km/h. Las borrascas nacen y se ahondan en sus bordes, así que conviene mirarla siempre.` });
    const upper = { dana: "una bolsa de aire frío aislada en altura; debajo, el aire se vuelve inestable",
      "baja-fria-en-altura": "un núcleo de aire frío cerrado en altura, que empuja a la borrasca de abajo",
      vaguada: "las líneas se doblan hacia el sur: aire frío que baja y, por delante, tiempo revuelto",
      dorsal: "las líneas se doblan hacia el norte: aire cálido y, debajo, tiempo tranquilo",
      bloqueo: "una alta en altura que frena el paso de las borrascas durante días" };
    for (const kind of Object.keys(upper)) {  // the first upper-air feature found, in this order
      const first = steps.map((h) => ({ h, f: (DAY.markers[h] || []).find((f) => f.kind === kind && near(f)) })).find((x) => x.f);
      if (!first) continue;
      stops.push({ f: first.f, h: first.h, zoom: 4, ids: "z500", concept: first.f.concept,
        html: `<b>El mapa de 500 hPa.</b> Las isohipsas dicen a qué altura se alcanzan los 500 hPa (552 = 5520 m). ` +
          `${KINDS[kind].name} ${first.f.where}: ${upper[kind]}.` });
      break;
    }
    const rain = extreme("lluvia-intensa", "max_mm");
    if (rain) stops.push({ f: rain.f, h: rain.h, zoom: 4, ids: "precip+msl", concept: "precipitacion",
      html: `<b>Precipitación.</b> Los colores son la lluvia acumulada en las 12 horas anteriores. El máximo, ` +
        `${fmtNum(rain.f.max_mm)} mm, cae ${rain.f.where} hasta el ${when(rain.h)}. Fíjate: la lluvia va pegada a las borrascas y a sus frentes.` });
    const cape = extreme("inestabilidad", "max_jkg");
    if (cape && cape.f.max_jkg >= 1000) stops.push({ f: cape.f, h: cape.h, zoom: 4, ids: "cape+msl", concept: "inestabilidad-y-cape",
      html: `<b>Energía para tormentas.</b> El CAPE mide cuánta energía tendría una burbuja de aire caliente para subir. ` +
        `Llega a ${fmtNum(cape.f.max_jkg)} J/kg ${cape.f.where}: si algo dispara el ascenso, ahí podrían crecer tormentas.` });
    const fc = DAY.focus;
    stops.push({ f: { lat: (fc.lat[0] + fc.lat[1]) / 2, lon: (fc.lon[0] + fc.lon[1]) / 2 }, h: DAY.defaultStep, zoom: 4,
      ids: "t850+msl", concept: "masas-de-aire",
      html: `<b>Temperatura a unos 1500 m (850 hPa).</b> Muestra las masas de aire sin el ruido del día y la noche: ` +
        "azules, aire frío; naranjas y rojos, aire cálido. Mueve la barra del tiempo y mira qué color avanza hacia la región foco (" + fc.name + ")." });
    stops.push({ f: { lat: 48, lon: 0 }, h: DAY.defaultStep, zoom: 3, ids: "sat+msl", concept: "satelite",
      html: "<b>Y ahora, la realidad.</b> El satélite muestra las nubes de verdad, casi en directo. Compara: " +
        "¿están las nubes donde el modelo pone las borrascas y la lluvia? Prueba también los canales de vapor de agua y de color." });
    return stops;
  }

  const tourBox = document.getElementById("tour");
  let tour = null;
  function showStop(i) {
    const s = tour[i];
    tour.i = i;
    state.layers = new Set(s.ids.split("+"));
    state.step = s.h;
    applyStep();
    const c = CONCEPTS[s.concept];
    tourBox.innerHTML = `<p class="label">Cómo leer el mapa · ${i + 1} de ${tour.length}</p><p>${s.html}</p>` +
      (c ? `<p><a href="#" class="concept" data-concept="${s.concept}">Ficha: ${c.title}</a></p>` : "") +
      `<div class="tour-nav"><button type="button" data-go="${i - 1}"${i ? "" : " disabled"}>← Anterior</button>` +
      (i < tour.length - 1 ? `<button type="button" data-go="close">Cerrar</button><button type="button" data-go="${i + 1}">Siguiente →</button>`
        : `<button type="button" data-go="close">Terminar</button>`) + "</div>";
    tourBox.hidden = false;
    // the card sits over the lower part of the map: put the feature in the free space above it
    const free = map.getContainer().clientHeight - tourBox.offsetHeight - 56;
    map.flyTo({ center: [s.f.lon, s.f.lat], zoom: s.zoom, speed: 1.3,
      offset: [0, Math.min(0, free / 2 - map.getContainer().clientHeight / 2)] });
  }
  if (tourBox) {
    document.getElementById("tourbtn").addEventListener("click", () => {
      tour = tourStops();
      showStop(0);
      document.querySelector(".mapbox").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    tourBox.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-go]");
      if (!b) return;
      if (b.dataset.go === "close") { tourBox.hidden = true; return; }
      showStop(Number(b.dataset.go));
    });
  }

  /* ------------------------------------------------------------------ quiz */

  const quiz = document.getElementById("quiz");
  if (quiz) {
    const key = "aulameteo.quiz." + DAY.date;
    let answers = {};
    try { answers = JSON.parse(localStorage.getItem(key)) || {}; } catch (e) { /* ignore */ }
    const items = [...quiz.querySelectorAll("li.q")];
    const mark = (li, chosen) => {
      const right = Number(li.dataset.correct);
      li.querySelectorAll(".opts button").forEach((b, i) => {
        b.disabled = true;
        if (i === right) b.classList.add("right");
        else if (i === chosen) b.classList.add("wrong");
      });
      li.querySelector(".why").hidden = false;
      li.classList.add(chosen === right ? "ok" : "ko");
    };
    const score = () => {
      const done = items.filter((li, i) => answers[i] != null);
      const ok = items.filter((li, i) => answers[i] === Number(li.dataset.correct)).length;
      quiz.querySelector(".score").textContent = done.length === items.length
        ? `Has acertado ${ok} de ${items.length}.` + (ok === items.length ? " ¡Ya sabes leer el mapa de hoy!" : " Repasa las fichas enlazadas y vuelve mañana.")
        : done.length ? `Llevas ${ok} de ${done.length}.` : "";
    };
    items.forEach((li, qi) => {
      if (answers[qi] != null) mark(li, answers[qi]);
      li.querySelectorAll(".opts button").forEach((b, i) => b.addEventListener("click", () => {
        answers[qi] = i;
        try { localStorage.setItem(key, JSON.stringify(answers)); } catch (e) { /* ignore */ }
        mark(li, i);
        score();
      }));
    });
    score();
  }  // pasted or back/forward #ver: links

  buildControls();
})();
