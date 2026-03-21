import { useState, useEffect } from 'react';
import { getStation, getYearlyRainfall, getRainfallStats, ApiError } from '../api/index.ts';
import type { StationDetail, RainfallYearly, RainfallStats } from '../types/index.ts';

interface UseStationDetailResult {
  station: StationDetail | null;
  stats: RainfallStats | null;
  yearlyData: RainfallYearly[];
  loading: boolean;
  error: string | null;
}

export function useStationDetail(stationId: string | null): UseStationDetailResult {
  const [station, setStation] = useState<StationDetail | null>(null);
  const [stats, setStats] = useState<RainfallStats | null>(null);
  const [yearlyData, setYearlyData] = useState<RainfallYearly[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!stationId) {
      setStation(null);
      setStats(null);
      setYearlyData([]);
      return;
    }

    let cancelled = false;

    async function fetchAll(id: string) {
      setLoading(true);
      setError(null);
      try {
        const [stationData, statsData, yearlyResponse] = await Promise.all([
          getStation(id),
          getRainfallStats(id).catch(() => null),
          getYearlyRainfall(id).catch(() => ({ data: [] })),
        ]);

        if (cancelled) return;
        setStation(stationData);
        setStats(statsData);
        setYearlyData(yearlyResponse.data);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Failed to load station details');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll(stationId);

    return () => {
      cancelled = true;
    };
  }, [stationId]);

  return { station, stats, yearlyData, loading, error };
}
