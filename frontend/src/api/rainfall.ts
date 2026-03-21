import { apiFetch } from './client.ts';
import type { YearlyResponse, RainfallStats } from '../types/index.ts';

export async function getYearlyRainfall(stationId: string): Promise<YearlyResponse> {
  return apiFetch<YearlyResponse>(`/api/rainfall/${encodeURIComponent(stationId)}/yearly`);
}

export async function getRainfallStats(stationId: string): Promise<RainfallStats> {
  return apiFetch<RainfallStats>(`/api/rainfall/${encodeURIComponent(stationId)}/stats`);
}
