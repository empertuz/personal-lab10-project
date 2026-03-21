from math import asin, cos, radians, sin, sqrt


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two WGS84 points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lon_min, lon_max) for a circle."""
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.0 * cos(radians(lat)))
    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)


def register_haversine_udf(conn) -> None:
    """Register the haversine function on a sqlite3/aiosqlite connection."""
    conn.create_function("haversine", 4, haversine)
