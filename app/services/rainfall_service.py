from datetime import date

import aiosqlite
from fastapi import HTTPException

from app.models.rainfall import (
    AreaMonthlyRequest,
    AreaMonthlyResponse,
    DailyResponse,
    MonthlyResponse,
    RainfallDaily,
    RainfallMonthly,
    RainfallStats,
    RainfallYearly,
    StationMonthlyData,
    YearlyResponse,
)
from app.services.geo import bounding_box


async def _check_station(db: aiosqlite.Connection, station_id: str) -> None:
    row = await db.execute_fetchall("SELECT id FROM stations WHERE id = ?", (station_id,))
    if not row:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")


async def get_daily(
    db: aiosqlite.Connection,
    station_id: str,
    date_from: str,
    date_to: str,
) -> DailyResponse:
    await _check_station(db, station_id)

    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to must be >= date_from")

    rows = await db.execute_fetchall(
        """SELECT date, value_mm FROM rainfall_daily
           WHERE station_id = ? AND date BETWEEN ? AND ?
           ORDER BY date""",
        (station_id, date_from, date_to),
    )
    return DailyResponse(
        station_id=station_id,
        date_from=date_from,
        date_to=date_to,
        count=len(rows),
        data=[RainfallDaily(date=r["date"], value_mm=r["value_mm"]) for r in rows],
    )


async def get_monthly(
    db: aiosqlite.Connection,
    station_id: str,
    year_from: int,
    year_to: int,
) -> MonthlyResponse:
    await _check_station(db, station_id)

    if year_to < year_from:
        raise HTTPException(status_code=422, detail="year_to must be >= year_from")

    rows = await db.execute_fetchall(
        """SELECT year, month, total_mm, avg_mm, max_mm, rainy_days, data_days
           FROM rainfall_monthly
           WHERE station_id = ? AND year BETWEEN ? AND ?
           ORDER BY year, month""",
        (station_id, year_from, year_to),
    )
    return MonthlyResponse(
        station_id=station_id,
        year_from=year_from,
        year_to=year_to,
        count=len(rows),
        data=[
            RainfallMonthly(
                year=r["year"],
                month=r["month"],
                total_mm=r["total_mm"],
                avg_mm=round(r["avg_mm"], 2) if r["avg_mm"] else 0,
                max_mm=r["max_mm"],
                rainy_days=r["rainy_days"],
                data_days=r["data_days"],
            )
            for r in rows
        ],
    )


async def get_yearly(db: aiosqlite.Connection, station_id: str) -> YearlyResponse:
    await _check_station(db, station_id)

    rows = await db.execute_fetchall(
        """SELECT year, total_mm, avg_daily_mm, max_daily_mm, rainy_days, data_days
           FROM rainfall_yearly
           WHERE station_id = ?
           ORDER BY year""",
        (station_id,),
    )
    return YearlyResponse(
        station_id=station_id,
        count=len(rows),
        data=[
            RainfallYearly(
                year=r["year"],
                total_mm=r["total_mm"],
                avg_daily_mm=round(r["avg_daily_mm"], 2) if r["avg_daily_mm"] else 0,
                max_daily_mm=r["max_daily_mm"],
                rainy_days=r["rainy_days"],
                data_days=r["data_days"],
            )
            for r in rows
        ],
    )


async def get_stats(db: aiosqlite.Connection, station_id: str) -> RainfallStats:
    await _check_station(db, station_id)

    row = await db.execute_fetchall(
        """SELECT
              MIN(date) as date_from,
              MAX(date) as date_to,
              COUNT(*) as total_records,
              AVG(value_mm) as avg_mm,
              MAX(value_mm) as max_mm,
              MIN(value_mm) as min_mm
           FROM rainfall_daily
           WHERE station_id = ?""",
        (station_id,),
    )
    r = row[0]

    coverage_pct = None
    if r["date_from"] and r["date_to"]:
        try:
            d_from = date.fromisoformat(r["date_from"])
            d_to = date.fromisoformat(r["date_to"])
            total_days = (d_to - d_from).days + 1
            if total_days > 0:
                coverage_pct = round(r["total_records"] / total_days * 100, 2)
        except ValueError:
            pass

    return RainfallStats(
        station_id=station_id,
        date_from=r["date_from"],
        date_to=r["date_to"],
        total_records=r["total_records"],
        avg_mm=round(r["avg_mm"], 2) if r["avg_mm"] is not None else None,
        max_mm=r["max_mm"],
        min_mm=r["min_mm"],
        coverage_pct=coverage_pct,
    )


async def get_area_monthly(
    db: aiosqlite.Connection, request: AreaMonthlyRequest
) -> AreaMonthlyResponse:
    if request.year_to < request.year_from:
        raise HTTPException(status_code=422, detail="year_to must be >= year_from")

    lat_min, lat_max, lon_min, lon_max = bounding_box(request.lat, request.lon, request.radius_km)

    station_rows = await db.execute_fetchall(
        """SELECT id, name, haversine(:lat, :lon, latitude, longitude) AS distance_km
           FROM stations
           WHERE latitude BETWEEN :lat_min AND :lat_max
             AND longitude BETWEEN :lon_min AND :lon_max
             AND haversine(:lat, :lon, latitude, longitude) <= :radius_km
             AND has_data = TRUE
           ORDER BY distance_km""",
        {
            "lat": request.lat,
            "lon": request.lon,
            "lat_min": lat_min,
            "lat_max": lat_max,
            "lon_min": lon_min,
            "lon_max": lon_max,
            "radius_km": request.radius_km,
        },
    )

    stations = []
    for s in station_rows:
        monthly_rows = await db.execute_fetchall(
            """SELECT year, month, total_mm, avg_mm, max_mm, rainy_days, data_days
               FROM rainfall_monthly
               WHERE station_id = ? AND year BETWEEN ? AND ?
               ORDER BY year, month""",
            (s["id"], request.year_from, request.year_to),
        )
        stations.append(
            StationMonthlyData(
                station_id=s["id"],
                station_name=s["name"],
                distance_km=round(s["distance_km"], 2),
                monthly=[
                    RainfallMonthly(
                        year=r["year"],
                        month=r["month"],
                        total_mm=r["total_mm"],
                        avg_mm=round(r["avg_mm"], 2) if r["avg_mm"] else 0,
                        max_mm=r["max_mm"],
                        rainy_days=r["rainy_days"],
                        data_days=r["data_days"],
                    )
                    for r in monthly_rows
                ],
            )
        )

    return AreaMonthlyResponse(
        center={"lat": request.lat, "lon": request.lon},
        radius_km=request.radius_km,
        year_from=request.year_from,
        year_to=request.year_to,
        stations=stations,
    )
