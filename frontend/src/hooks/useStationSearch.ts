import { useState, useCallback } from 'react';
import { searchStations, ApiError } from '../api/index.ts';
import type { StationSearchParams, StationSearchResponse } from '../types/index.ts';

interface UseStationSearchResult {
  results: StationSearchResponse | null;
  loading: boolean;
  error: string | null;
  search: (params: StationSearchParams) => Promise<void>;
  clear: () => void;
}

export function useStationSearch(): UseStationSearchResult {
  const [results, setResults] = useState<StationSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (params: StationSearchParams) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchStations({ ...params, include_summary: true });
      setResults(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred');
      }
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults(null);
    setError(null);
  }, []);

  return { results, loading, error, search, clear };
}
