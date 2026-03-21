from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.models.station import (
    StationDetail,
    StationListParams,
    StationListResponse,
    StationSearchParams,
    StationSearchResponse,
)
from app.services import station_service

router = APIRouter(prefix="/api/stations", tags=["stations"])


def _get_db(request: Request):
    return request.app.state.db


@router.get("/search", response_model=StationSearchResponse)
async def search_stations(
    lat: float = Query(..., ge=-4.0, le=13.5),
    lon: float = Query(..., ge=-82.0, le=-66.0),
    radius_km: float = Query(..., gt=0, le=500),
    status: Optional[str] = None,
    category: Optional[str] = None,
    has_data: Optional[bool] = None,
    include_summary: bool = False,
    db=Depends(_get_db),
):
    params = StationSearchParams(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        status=status,
        category=category,
        has_data=has_data,
        include_summary=include_summary,
    )
    stations = await station_service.search_stations(db, params)
    return StationSearchResponse(
        center={"lat": lat, "lon": lon},
        radius_km=radius_km,
        count=len(stations),
        stations=stations,
    )


@router.get("/{station_id}", response_model=StationDetail)
async def get_station(station_id: str, db=Depends(_get_db)):
    station = await station_service.get_station(db, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/", response_model=StationListResponse)
async def list_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    department: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db=Depends(_get_db),
):
    params = StationListParams(
        page=page,
        page_size=page_size,
        department=department,
        status=status,
        category=category,
    )
    total, stations = await station_service.list_stations(db, params)
    return StationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        stations=stations,
    )
