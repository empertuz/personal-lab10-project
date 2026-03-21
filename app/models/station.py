from typing import Optional

from pydantic import BaseModel, Field


class StationSearchParams(BaseModel):
    lat: float = Field(..., ge=-4.0, le=13.5)
    lon: float = Field(..., ge=-82.0, le=-66.0)
    radius_km: float = Field(..., gt=0, le=500)
    status: Optional[str] = None
    category: Optional[str] = None
    has_data: Optional[bool] = None
    include_summary: bool = False


class DataSummary(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    total_records: int = 0


class StationResponse(BaseModel):
    id: str
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    department: Optional[str] = None
    municipality: Optional[str] = None
    distance_km: float
    has_data: bool
    data_summary: Optional[DataSummary] = None


class StationDetail(BaseModel):
    id: str
    name: Optional[str] = None
    category: Optional[str] = None
    technology: Optional[str] = None
    status: Optional[str] = None
    installed_at: Optional[str] = None
    suspended_at: Optional[str] = None
    altitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    department: Optional[str] = None
    municipality: Optional[str] = None
    operational_area: Optional[str] = None
    hydro_area: Optional[str] = None
    hydro_zone: Optional[str] = None
    hydro_subzone: Optional[str] = None
    stream: Optional[str] = None
    has_data: bool = False
    data_summary: Optional[DataSummary] = None


class StationListParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(100, ge=1, le=500)
    department: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None


class StationSearchResponse(BaseModel):
    center: dict
    radius_km: float
    count: int
    stations: list[StationResponse]


class StationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    stations: list[StationDetail]
