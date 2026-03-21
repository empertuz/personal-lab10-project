import pytest


@pytest.mark.asyncio
async def test_daily_returns_data(async_client):
    resp = await async_client.get(
        "/api/rainfall/11010010/daily",
        params={"date_from": "2020-01-01", "date_to": "2020-12-31"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["station_id"] == "11010010"
    assert data["count"] == 4  # 3 Jan + 1 Jun
    assert all("date" in d and "value_mm" in d for d in data["data"])


@pytest.mark.asyncio
async def test_daily_invalid_range(async_client):
    resp = await async_client.get(
        "/api/rainfall/11010010/daily",
        params={"date_from": "2020-12-31", "date_to": "2020-01-01"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_monthly_aggregation(async_client):
    resp = await async_client.get(
        "/api/rainfall/11010010/monthly",
        params={"year_from": 2020, "year_to": 2020},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Jan and Jun
    jan = next(m for m in data["data"] if m["month"] == 1)
    assert jan["total_mm"] == 17.5


@pytest.mark.asyncio
async def test_yearly(async_client):
    resp = await async_client.get("/api/rainfall/11010010/yearly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["data"][0]["year"] == 2020
    assert data["data"][0]["total_mm"] == 47.5


@pytest.mark.asyncio
async def test_stats_endpoint(async_client):
    resp = await async_client.get("/api/rainfall/11010010/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] == 4
    assert data["date_from"] == "2020-01-01"
    assert data["date_to"] == "2020-06-15"
    assert data["max_mm"] == 30.0
    assert data["min_mm"] == 0.0
    assert data["coverage_pct"] is not None


@pytest.mark.asyncio
async def test_area_monthly(async_client):
    resp = await async_client.post(
        "/api/rainfall/area/monthly",
        json={
            "lat": 5.45,
            "lon": -76.55,
            "radius_km": 50,
            "year_from": 2020,
            "year_to": 2020,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["stations"]) >= 1


@pytest.mark.asyncio
async def test_rainfall_unknown_station(async_client):
    resp = await async_client.get(
        "/api/rainfall/DOESNOTEXIST/daily",
        params={"date_from": "2020-01-01", "date_to": "2020-12-31"},
    )
    assert resp.status_code == 404
