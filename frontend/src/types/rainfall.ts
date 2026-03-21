export interface RainfallYearly {
  year: number;
  total_mm: number;
  avg_daily_mm: number;
  max_daily_mm: number;
  rainy_days: number;
  data_days: number;
}

export interface YearlyResponse {
  station_id: string;
  count: number;
  data: RainfallYearly[];
}

export interface RainfallStats {
  station_id: string;
  date_from: string | null;
  date_to: string | null;
  total_records: number;
  avg_mm: number | null;
  max_mm: number | null;
  min_mm: number | null;
  coverage_pct: number | null;
}

export interface HealthResponse {
  status: string;
  tables: Record<string, number>;
}
