import { apiFetch } from './client.ts';
import type { HealthResponse } from '../types/index.ts';

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/api/health');
}
