"""Tiny gazetteer so detected systems can be described in words ("a 300 km al oeste de Galicia")."""
import math

# (name, lat, lon). Mix of land regions, cities and seas across the domain.
PLACES = [
    ("Galicia", 42.8, -8.0), ("Asturias", 43.3, -5.9), ("País Vasco", 43.0, -2.6),
    ("Cataluña", 41.8, 1.7), ("Comunidad Valenciana", 39.4, -0.6), ("Murcia", 38.0, -1.2),
    ("Andalucía occidental", 37.4, -6.0), ("Andalucía oriental", 37.2, -3.5),
    ("Extremadura", 39.2, -6.2), ("Castilla y León", 41.7, -4.7), ("Madrid", 40.4, -3.7),
    ("Castilla-La Mancha", 39.4, -3.0), ("Aragón", 41.6, -0.9), ("Baleares", 39.6, 2.9),
    ("Canarias", 28.3, -15.8), ("Portugal", 39.6, -8.2), ("Lisboa", 38.7, -9.1),
    ("el golfo de Cádiz", 36.4, -7.5), ("el mar de Alborán", 36.0, -3.5),
    ("el golfo de Vizcaya", 45.5, -4.5), ("el golfo de León", 42.8, 4.3),
    ("Bretaña", 48.2, -3.0), ("París", 48.9, 2.4), ("el sur de Francia", 44.0, 2.0),
    ("los Alpes", 46.5, 10.0), ("el norte de Italia", 45.3, 9.5), ("Roma", 41.9, 12.5),
    ("Cerdeña", 40.1, 9.0), ("Sicilia", 37.5, 14.0), ("el mar Tirreno", 40.0, 12.0),
    ("el mar Adriático", 43.0, 15.5), ("los Balcanes", 43.5, 20.5), ("Grecia", 39.0, 22.0),
    ("el mar Egeo", 38.5, 25.0), ("Turquía", 39.0, 33.0), ("el mar Negro", 43.5, 34.0),
    ("Chipre", 35.0, 33.0), ("Túnez", 35.5, 9.5), ("Argelia", 34.0, 3.0),
    ("Marruecos", 32.0, -6.0), ("el norte de Libia", 31.0, 17.0), ("Egipto", 28.0, 30.0),
    ("Madeira", 32.7, -17.0), ("Azores", 38.5, -28.0), ("Irlanda", 53.2, -8.0),
    ("Londres", 51.5, -0.1), ("Escocia", 56.8, -4.2), ("el mar del Norte", 56.0, 3.0),
    ("Países Bajos", 52.3, 5.5), ("Alemania", 51.0, 10.0), ("Polonia", 52.0, 19.5),
    ("Chequia", 49.8, 15.5), ("Hungría", 47.2, 19.4), ("Rumanía", 45.8, 25.0),
    ("Ucrania", 49.0, 31.5), ("Bielorrusia", 53.7, 28.0), ("Moscú", 55.8, 37.6),
    ("los países bálticos", 56.5, 24.5), ("el mar Báltico", 57.5, 19.0),
    ("Dinamarca", 56.0, 9.5), ("el sur de Noruega", 60.5, 8.5), ("Suecia", 62.0, 16.0),
    ("Finlandia", 63.0, 26.0), ("el norte de Escandinavia", 68.5, 20.0),
    ("Islandia", 64.9, -18.6), ("el mar de Noruega", 67.0, 3.0),
    ("el sur de Groenlandia", 62.0, -44.0), ("el Atlántico norte", 55.0, -30.0),
    ("el Atlántico central", 40.0, -35.0), ("el Atlántico, al oeste de Irlanda", 53.0, -18.0),
    ("el Atlántico, al oeste de la península", 41.0, -18.0),
    ("el Atlántico, al norte de Canarias", 32.0, -20.0),
    ("el Atlántico, al este de Terranova", 48.0, -40.0), ("el mar de Irminger", 60.0, -35.0),
    ("el mar de Barents", 72.0, 35.0), ("el norte de Rusia", 64.0, 42.0),
    ("los Urales", 58.0, 50.0), ("el mar Caspio", 42.0, 50.0), ("el Cáucaso", 42.5, 44.0),
    ("el Sáhara argelino", 29.0, 3.0), ("el Sáhara occidental", 26.5, -12.0),
]

_DIRS = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def describe(lat: float, lon: float) -> str:
    """'sobre Galicia' when close, else 'a 400 km al oeste de Galicia'."""
    name, plat, plon = min(PLACES, key=lambda p: distance_km(lat, lon, p[1], p[2]))
    d = distance_km(lat, lon, plat, plon)
    if d < 150:
        return f"sobre {name}"
    direction = _DIRS[int((_bearing(plat, plon, lat, lon) + 22.5) // 45) % 8]
    of = "del " + name[3:] if name.startswith("el ") else "de " + name
    return f"a unos {round(d, -1):.0f} km al {direction} {of}"
