import { useState, useCallback, lazy, Suspense } from 'react';
import { useStationSearch } from './hooks/useStationSearch.ts';
import { SearchPanel } from './components/search/SearchPanel.tsx';
import { StationList } from './components/stations/StationList.tsx';
import { StationDetail } from './components/stations/StationDetail.tsx';
import { LoadingSpinner } from './components/common/LoadingSpinner.tsx';
import { ErrorMessage } from './components/common/ErrorMessage.tsx';
import { EmptyState } from './components/common/EmptyState.tsx';

const StationMap = lazy(() =>
  import('./components/map/StationMap.tsx').then((m) => ({ default: m.StationMap })),
);

type ViewState = 'search' | 'results' | 'detail';

function App() {
  const [view, setView] = useState<ViewState>('search');
  const [clickedLocation, setClickedLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [selectedStationId, setSelectedStationId] = useState<string | null>(null);
  const [detailStationId, setDetailStationId] = useState<string | null>(null);
  const [showMapView, setShowMapView] = useState(false);

  const { results, loading, error, search, clear } = useStationSearch();

  const handleMapClick = useCallback((lat: number, lon: number) => {
    setClickedLocation({ lat, lon });
  }, []);

  const handleSearch = useCallback(
    async (lat: number, lon: number, radiusKm: number) => {
      setClickedLocation({ lat, lon });
      setSelectedStationId(null);
      await search({ lat, lon, radius_km: radiusKm });
      setView('results');
    },
    [search],
  );

  const handleStationClick = useCallback((stationId: string) => {
    setSelectedStationId((prev) => (prev === stationId ? null : stationId));
  }, []);

  const handleViewDetails = useCallback((stationId: string) => {
    setDetailStationId(stationId);
    setView('detail');
  }, []);

  const handleBackToSearch = useCallback(() => {
    setView('search');
    setClickedLocation(null);
    setSelectedStationId(null);
    clear();
  }, [clear]);

  const handleBackToResults = useCallback(() => {
    setView('results');
    setDetailStationId(null);
  }, []);

  // Panel content based on view state
  function renderPanel() {
    switch (view) {
      case 'search':
        return (
          <SearchPanel
            key={clickedLocation ? `${clickedLocation.lat},${clickedLocation.lon}` : 'empty'}
            initialLat={clickedLocation ? clickedLocation.lat.toFixed(4) : ''}
            initialLon={clickedLocation ? clickedLocation.lon.toFixed(4) : ''}
            onSearch={handleSearch}
            loading={loading}
          />
        );

      case 'results':
        if (loading) return <LoadingSpinner message="Searching stations..." />;
        if (error) return <ErrorMessage message={error} onRetry={() => setView('search')} />;
        if (!results || results.count === 0)
          return (
            <div className="space-y-3 rounded-xl bg-white/95 p-4 shadow-lg backdrop-blur-sm lg:w-80">
              <EmptyState />
              <button
                onClick={handleBackToSearch}
                className="w-full rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
              >
                ← New search
              </button>
            </div>
          );
        return (
          <div className="flex max-h-[calc(100vh-2rem)] flex-col rounded-xl bg-white/95 shadow-lg backdrop-blur-sm lg:w-80">
            {/* Mobile toggle */}
            <div className="flex border-b border-gray-100 p-2 lg:hidden">
              <button
                onClick={() => setShowMapView(false)}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${
                  !showMapView ? 'bg-blue-100 text-blue-700' : 'text-gray-500'
                }`}
              >
                List
              </button>
              <button
                onClick={() => setShowMapView(true)}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${
                  showMapView ? 'bg-blue-100 text-blue-700' : 'text-gray-500'
                }`}
              >
                Map
              </button>
            </div>
            <div className={showMapView ? 'hidden lg:block' : ''}>
              <StationList
                stations={results.stations}
                count={results.count}
                radiusKm={results.radius_km}
                selectedStationId={selectedStationId}
                onStationClick={handleViewDetails}
                onBack={handleBackToSearch}
              />
            </div>
          </div>
        );

      case 'detail':
        if (!detailStationId) return null;
        return (
          <div className="flex max-h-[calc(100vh-2rem)] flex-col rounded-xl bg-white/95 shadow-lg backdrop-blur-sm lg:w-96">
            <StationDetail stationId={detailStationId} onBack={handleBackToResults} />
          </div>
        );
    }
  }

  return (
    <main className="relative h-full w-full">
      {/* Map background */}
      <Suspense
        fallback={
          <div className="flex h-full items-center justify-center bg-gray-100">
            <LoadingSpinner message="Loading map..." />
          </div>
        }
      >
        <StationMap
          onMapClick={handleMapClick}
          clickedLocation={clickedLocation}
          searchCenter={results?.center ?? null}
          searchRadius={results?.radius_km ?? null}
          stations={results?.stations ?? []}
          selectedStationId={selectedStationId}
          onMarkerClick={handleStationClick}
          onPopupViewDetails={handleViewDetails}
        />
      </Suspense>

      {/* Floating panel */}
      <div
        className="absolute top-0 left-0 z-10 max-h-full w-full p-4 lg:w-auto"
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        {renderPanel()}
      </div>
    </main>
  );
}

export default App;
