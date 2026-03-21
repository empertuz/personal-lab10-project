export interface StationSearchParams {
  lat: number;
  lon: number;
  radius_km: number;
  status?: string;
  category?: string;
  has_data?: boolean;
  include_summary?: boolean;
}

export interface DataSummary {
  date_from: string | null;
  date_to: string | null;
  total_records: number;
}

export interface StationResponse {
  id: string;
  name: string | null;
  category: string | null;
  status: string | null;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  department: string | null;
  municipality: string | null;
  distance_km: number;
  has_data: boolean;
  data_summary: DataSummary | null;
}

export interface StationDetail {
  id: string;
  name: string | null;
  category: string | null;
  technology: string | null;
  status: string | null;
  installed_at: string | null;
  suspended_at: string | null;
  altitude: number | null;
  latitude: number | null;
  longitude: number | null;
  department: string | null;
  municipality: string | null;
  operational_area: string | null;
  hydro_area: string | null;
  hydro_zone: string | null;
  hydro_subzone: string | null;
  stream: string | null;
  has_data: boolean;
  data_summary: DataSummary | null;
}

export interface StationSearchResponse {
  center: { lat: number; lon: number };
  radius_km: number;
  count: number;
  stations: StationResponse[];
}
