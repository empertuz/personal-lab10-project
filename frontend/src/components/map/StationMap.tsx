import { useCallback, useMemo, useRef } from 'react';
import Map, {
  Marker,
  Popup,
  Source,
  Layer,
  type MapMouseEvent,
  type MapRef,
} from 'react-map-gl/mapbox';
import circle from '@turf/circle';
import type { StationResponse } from '../../types/index.ts';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string;

const COLOMBIA_CENTER = { latitude: 4.5, longitude: -73.5 };
const INITIAL_ZOOM = 5.5;

interface StationMapProps {
  onMapClick?: (lat: number, lon: number) => void;
  searchCenter?: { lat: number; lon: number } | null;
  searchRadius?: number | null;
  stations?: StationResponse[];
  selectedStationId?: string | null;
  onMarkerClick?: (stationId: string) => void;
  onPopupViewDetails?: (stationId: string) => void;
  clickedLocation?: { lat: number; lon: number } | null;
}

export function StationMap({
  onMapClick,
  searchCenter,
  searchRadius,
  stations = [],
  selectedStationId,
  onMarkerClick,
  onPopupViewDetails,
  clickedLocation,
}: StationMapProps) {
  const mapRef = useRef<MapRef>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleClick = useCallback(
    (e: MapMouseEvent) => {
      if (!onMapClick) return;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onMapClick(e.lngLat.lat, e.lngLat.lng);
      }, 150);
    },
    [onMapClick],
  );

  const circleGeoJSON = useMemo(() => {
    if (!searchCenter || !searchRadius) return null;
    return circle([searchCenter.lon, searchCenter.lat], searchRadius, {
      steps: 64,
      units: 'kilometers',
    });
  }, [searchCenter, searchRadius]);

  const selectedStation = useMemo(
    () => stations.find((s) => s.id === selectedStationId) ?? null,
    [stations, selectedStationId],
  );

  return (
    <Map
      ref={mapRef}
      mapboxAccessToken={MAPBOX_TOKEN}
      initialViewState={{
        ...COLOMBIA_CENTER,
        zoom: INITIAL_ZOOM,
      }}
      style={{ width: '100%', height: '100%' }}
      mapStyle="mapbox://styles/mapbox/outdoors-v12"
      onClick={handleClick}
      cursor="crosshair"
    >
      {/* Clicked location marker */}
      {clickedLocation && (
        <Marker latitude={clickedLocation.lat} longitude={clickedLocation.lon} anchor="bottom">
          <div className="text-2xl">📍</div>
        </Marker>
      )}

      {/* Search radius circle */}
      {circleGeoJSON && (
        <Source id="search-radius" type="geojson" data={circleGeoJSON}>
          <Layer
            id="search-radius-fill"
            type="fill"
            paint={{
              'fill-color': '#3b82f6',
              'fill-opacity': 0.1,
            }}
          />
          <Layer
            id="search-radius-line"
            type="line"
            paint={{
              'line-color': '#3b82f6',
              'line-width': 2,
              'line-dasharray': [2, 2],
            }}
          />
        </Source>
      )}

      {/* Station markers */}
      {stations
        .filter((s) => s.latitude != null && s.longitude != null)
        .map((station) => (
          <Marker
            key={station.id}
            latitude={station.latitude!}
            longitude={station.longitude!}
            anchor="bottom"
            onClick={(e: { originalEvent: MouseEvent }) => {
              e.originalEvent.stopPropagation();
              onMarkerClick?.(station.id);
            }}
          >
            <div
              className={`flex h-6 w-6 cursor-pointer items-center justify-center rounded-full border-2 border-white shadow-md transition-transform ${
                station.has_data && station.status === 'Activa'
                  ? 'bg-green-500'
                  : station.has_data
                    ? 'bg-yellow-500'
                    : 'bg-gray-400'
              } ${station.id === selectedStationId ? 'scale-125 ring-2 ring-blue-500' : ''}`}
              title={station.name ?? station.id}
            >
              <span className="text-[8px] font-bold text-white">●</span>
            </div>
          </Marker>
        ))}

      {/* Popup for selected station */}
      {selectedStation && selectedStation.latitude != null && selectedStation.longitude != null && (
        <Popup
          latitude={selectedStation.latitude}
          longitude={selectedStation.longitude}
          anchor="bottom"
          offset={[0, -30]}
          closeOnClick={false}
          onClose={() => onMarkerClick?.(selectedStation.id)}
        >
          <div className="min-w-[180px] p-1">
            <h3 className="text-sm font-semibold text-gray-900">
              {selectedStation.name ?? selectedStation.id}
            </h3>
            <div className="mt-1 space-y-0.5 text-xs text-gray-600">
              <p>
                <span className="font-medium">Status:</span>{' '}
                <span
                  className={
                    selectedStation.status === 'Activa' ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {selectedStation.status ?? '—'}
                </span>
              </p>
              <p>
                <span className="font-medium">Distance:</span>{' '}
                {selectedStation.distance_km.toFixed(1)} km
              </p>
              {selectedStation.department && (
                <p>
                  <span className="font-medium">Dept:</span> {selectedStation.department}
                </p>
              )}
            </div>
            <button
              onClick={() => onPopupViewDetails?.(selectedStation.id)}
              className="mt-2 w-full rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              View details
            </button>
          </div>
        </Popup>
      )}
    </Map>
  );
}
