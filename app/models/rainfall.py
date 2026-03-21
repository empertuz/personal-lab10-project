from typing import Optional

from pydantic import BaseModel, Field


class RainfallDaily(BaseModel):
    date: str
    value_mm: float


class RainfallMonthly(BaseModel):
    year: int
    month: int
    total_mm: float
    avg_mm: float
    max_mm: float
    rainy_days: int
    data_days: int


class RainfallYearly(BaseModel):
    year: int
    total_mm: float
    avg_daily_mm: float
    max_daily_mm: float
    rainy_days: int
    data_days: int


class RainfallStats(BaseModel):
    station_id: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    total_records: int = 0
    avg_mm: Optional[float] = None
    max_mm: Optional[float] = None
    min_mm: Optional[float] = None
    coverage_pct: Optional[float] = None


class AreaMonthlyRequest(BaseModel):
    lat: float = Field(..., ge=-4.0, le=13.5)
    lon: float = Field(..., ge=-82.0, le=-66.0)
    radius_km: float = Field(..., gt=0, le=500)
    year_from: int
    year_to: int


class StationMonthlyData(BaseModel):
    station_id: str
    station_name: Optional[str] = None
    distance_km: float
    monthly: list[RainfallMonthly]


class AreaMonthlyResponse(BaseModel):
    center: dict
    radius_km: float
    year_from: int
    year_to: int
    stations: list[StationMonthlyData]


class DailyResponse(BaseModel):
    station_id: str
    date_from: str
    date_to: str
    count: int
    data: list[RainfallDaily]


class MonthlyResponse(BaseModel):
    station_id: str
    year_from: int
    year_to: int
    count: int
    data: list[RainfallMonthly]


class YearlyResponse(BaseModel):
    station_id: str
    count: int
    data: list[RainfallYearly]
