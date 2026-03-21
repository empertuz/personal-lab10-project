from app.services.geo import bounding_box, haversine


def test_haversine_known_distance():
    # Medellín airport (6.2206, -75.5906) to city center approx (6.2518, -75.5636)
    dist = haversine(6.2206, -75.5906, 6.2518, -75.5636)
    assert 2.0 < dist < 5.0, f"Expected ~3.8 km, got {dist:.2f} km"


def test_haversine_zero_distance():
    assert haversine(6.25, -75.57, 6.25, -75.57) == 0.0


def test_haversine_long_distance():
    # Bogotá to Cartagena: ~650 km
    dist = haversine(4.711, -74.0721, 10.3910, -75.5364)
    assert 630 < dist < 680


def test_bounding_box_contains_point():
    lat, lon, radius = 6.25, -75.57, 50
    lat_min, lat_max, lon_min, lon_max = bounding_box(lat, lon, radius)
    # A point ~30 km away should be inside the bounding box
    point_lat, point_lon = 6.0, -75.5
    assert lat_min <= point_lat <= lat_max
    assert lon_min <= point_lon <= lon_max


def test_bounding_box_excludes_point():
    lat, lon, radius = 6.25, -75.57, 10
    lat_min, lat_max, lon_min, lon_max = bounding_box(lat, lon, radius)
    # A point ~100 km away should be outside the box
    point_lat = 7.2
    assert not (lat_min <= point_lat <= lat_max)
