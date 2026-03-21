import { apiFetch } from './client.ts';
import type { StationSearchParams, StationSearchResponse, StationDetail } from '../types/index.ts';

export async function searchStations(params: StationSearchParams): Promise<StationSearchResponse> {
  const query = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    radius_km: String(params.radius_km),
  });
  if (params.status) query.set('status', params.status);
  if (params.category) query.set('category', params.category);
  if (params.has_data !== undefined) query.set('has_data', String(params.has_data));
  if (params.include_summary) query.set('include_summary', 'true');

  return apiFetch<StationSearchResponse>(`/api/stations/search?${query}`);
}

export async function getStation(stationId: string): Promise<StationDetail> {
  return apiFetch<StationDetail>(`/api/stations/${encodeURIComponent(stationId)}`);
}
