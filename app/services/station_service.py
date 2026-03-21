from typing import Optional

import aiosqlite

from app.models.station import (
    DataSummary,
    StationDetail,
    StationListParams,
    StationResponse,
    StationSearchParams,
)
from app.services.geo import bounding_box


async def search_stations(
    db: aiosqlite.Connection, params: StationSearchParams
) -> list[StationResponse]:
    lat_min, lat_max, lon_min, lon_max = bounding_box(params.lat, params.lon, params.radius_km)

    sql = """
        SELECT id, name, category, status, latitude, longitude, altitude,
               department, municipality, has_data,
               haversine(:lat, :lon, latitude, longitude) AS distance_km
        FROM stations
        WHERE latitude BETWEEN :lat_min AND :lat_max
          AND longitude BETWEEN :lon_min AND :lon_max
          AND haversine(:lat, :lon, latitude, longitude) <= :radius_km
    """
    bind = {
        "lat": params.lat,
        "lon": params.lon,
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max,
        "radius_km": params.radius_km,
    }

    if params.status:
        sql += " AND status = :status"
        bind["status"] = params.status
    if params.category:
        sql += " AND category = :category"
        bind["category"] = params.category
    if params.has_data is not None:
        sql += " AND has_data = :has_data"
        bind["has_data"] = params.has_data

    sql += " ORDER BY distance_km"

    rows = await db.execute_fetchall(sql, bind)

    results = []
    for row in rows:
        summary = None
        if params.include_summary and row["has_data"]:
            summary = await _get_data_summary(db, row["id"])

        results.append(
            StationResponse(
                id=row["id"],
                name=row["name"],
                category=row["category"],
                status=row["status"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                altitude=row["altitude"],
                department=row["department"],
                municipality=row["municipality"],
                distance_km=round(row["distance_km"], 2),
                has_data=bool(row["has_data"]),
                data_summary=summary,
            )
        )

    return results


async def get_station(db: aiosqlite.Connection, station_id: str) -> Optional[StationDetail]:
    row = await db.execute_fetchall("SELECT * FROM stations WHERE id = ?", (station_id,))
    if not row:
        return None
    r = row[0]
    summary = await _get_data_summary(db, station_id) if r["has_data"] else None
    return StationDetail(
        id=r["id"],
        name=r["name"],
        category=r["category"],
        technology=r["technology"],
        status=r["status"],
        installed_at=r["installed_at"],
        suspended_at=r["suspended_at"],
        altitude=r["altitude"],
        latitude=r["latitude"],
        longitude=r["longitude"],
        department=r["department"],
        municipality=r["municipality"],
        operational_area=r["operational_area"],
        hydro_area=r["hydro_area"],
        hydro_zone=r["hydro_zone"],
        hydro_subzone=r["hydro_subzone"],
        stream=r["stream"],
        has_data=bool(r["has_data"]),
        data_summary=summary,
    )


async def list_stations(
    db: aiosqlite.Connection, params: StationListParams
) -> tuple[int, list[StationDetail]]:
    where_clauses = []
    bind: dict = {}

    if params.department:
        where_clauses.append("department = :department")
        bind["department"] = params.department
    if params.status:
        where_clauses.append("status = :status")
        bind["status"] = params.status
    if params.category:
        where_clauses.append("category = :category")
        bind["category"] = params.category

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    count_row = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM stations{where_sql}", bind)
    total = count_row[0]["cnt"]

    offset = (params.page - 1) * params.page_size
    bind["limit"] = params.page_size
    bind["offset"] = offset

    rows = await db.execute_fetchall(
        f"SELECT * FROM stations{where_sql} ORDER BY id LIMIT :limit OFFSET :offset",
        bind,
    )

    stations = [
        StationDetail(
            id=r["id"],
            name=r["name"],
            category=r["category"],
            technology=r["technology"],
            status=r["status"],
            installed_at=r["installed_at"],
            suspended_at=r["suspended_at"],
            altitude=r["altitude"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            department=r["department"],
            municipality=r["municipality"],
            operational_area=r["operational_area"],
            hydro_area=r["hydro_area"],
            hydro_zone=r["hydro_zone"],
            hydro_subzone=r["hydro_subzone"],
            stream=r["stream"],
            has_data=bool(r["has_data"]),
        )
        for r in rows
    ]
    return total, stations


async def _get_data_summary(db: aiosqlite.Connection, station_id: str) -> DataSummary:
    row = await db.execute_fetchall(
        """SELECT MIN(date) as date_from, MAX(date) as date_to, COUNT(*) as total_records
           FROM rainfall_daily WHERE station_id = ?""",
        (station_id,),
    )
    r = row[0]
    return DataSummary(
        date_from=r["date_from"],
        date_to=r["date_to"],
        total_records=r["total_records"],
    )
