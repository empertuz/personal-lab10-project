from fastapi import APIRouter, Depends, Query, Request

from app.models.rainfall import (
    AreaMonthlyRequest,
    AreaMonthlyResponse,
    DailyResponse,
    MonthlyResponse,
    RainfallStats,
    YearlyResponse,
)
from app.services import rainfall_service

router = APIRouter(prefix="/api/rainfall", tags=["rainfall"])


def _get_db(request: Request):
    return request.app.state.db


@router.get("/{station_id}/daily", response_model=DailyResponse)
async def get_daily(
    station_id: str,
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to: str = Query(..., description="YYYY-MM-DD"),
    db=Depends(_get_db),
):
    return await rainfall_service.get_daily(db, station_id, date_from, date_to)


@router.get("/{station_id}/monthly", response_model=MonthlyResponse)
async def get_monthly(
    station_id: str,
    year_from: int = Query(...),
    year_to: int = Query(...),
    db=Depends(_get_db),
):
    return await rainfall_service.get_monthly(db, station_id, year_from, year_to)


@router.get("/{station_id}/yearly", response_model=YearlyResponse)
async def get_yearly(station_id: str, db=Depends(_get_db)):
    return await rainfall_service.get_yearly(db, station_id)


@router.get("/{station_id}/stats", response_model=RainfallStats)
async def get_stats(station_id: str, db=Depends(_get_db)):
    return await rainfall_service.get_stats(db, station_id)


@router.post("/area/monthly", response_model=AreaMonthlyResponse)
async def area_monthly(body: AreaMonthlyRequest, db=Depends(_get_db)):
    return await rainfall_service.get_area_monthly(db, body)
