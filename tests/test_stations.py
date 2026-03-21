import pytest


@pytest.mark.asyncio
async def test_search_returns_results(async_client):
    # Search near Chocó station (5.45, -76.54) — should find LA VUELTA
    resp = await async_client.get(
        "/api/stations/search", params={"lat": 5.45, "lon": -76.55, "radius_km": 50}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert all("distance_km" in s for s in data["stations"])


@pytest.mark.asyncio
async def test_search_has_data_filter(async_client):
    # Station 99999999 has has_data=False, should be excluded
    resp = await async_client.get(
        "/api/stations/search",
        params={"lat": 7.0, "lon": -74.0, "radius_km": 50, "has_data": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    station_ids = [s["id"] for s in data["stations"]]
    assert "99999999" not in station_ids


@pytest.mark.asyncio
async def test_search_out_of_bounds_lat(async_client):
    resp = await async_client.get(
        "/api/stations/search", params={"lat": 20.0, "lon": -75.0, "radius_km": 10}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_station_detail_found(async_client):
    resp = await async_client.get("/api/stations/11010010")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "11010010"
    assert data["name"] == "LA VUELTA"
    assert data["has_data"] is True


@pytest.mark.asyncio
async def test_station_detail_not_found(async_client):
    resp = await async_client.get("/api/stations/DOESNOTEXIST")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_station_list_pagination(async_client):
    resp = await async_client.get("/api/stations/", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["stations"]) == 2
    assert data["page"] == 1
