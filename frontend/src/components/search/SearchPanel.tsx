import { useState, type FormEvent } from 'react';
import { isValidLat, isValidLon, isValidRadius, COLOMBIA_BOUNDS } from '../../utils/validation.ts';

interface SearchPanelProps {
  initialLat?: string;
  initialLon?: string;
  onSearch: (lat: number, lon: number, radiusKm: number) => void;
  loading?: boolean;
}

export function SearchPanel({
  initialLat = '',
  initialLon = '',
  onSearch,
  loading,
}: SearchPanelProps) {
  const [lat, setLat] = useState(initialLat);
  const [lon, setLon] = useState(initialLon);
  const [radius, setRadius] = useState('50');

  // Reset internal state when initial values change (via key prop from parent)
  if (lat === '' && initialLat !== '') setLat(initialLat);
  if (lon === '' && initialLon !== '') setLon(initialLon);

  const latNum = parseFloat(lat);
  const lonNum = parseFloat(lon);
  const radiusNum = parseFloat(radius);

  const latValid = lat !== '' && !isNaN(latNum) && isValidLat(latNum);
  const lonValid = lon !== '' && !isNaN(lonNum) && isValidLon(lonNum);
  const radiusValid = radius !== '' && !isNaN(radiusNum) && isValidRadius(radiusNum);
  const canSearch = latValid && lonValid && radiusValid && !loading;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSearch) {
      onSearch(latNum, lonNum, radiusNum);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full space-y-3 rounded-xl bg-white/95 p-4 shadow-lg backdrop-blur-sm lg:w-80"
    >
      <h2 className="text-base font-semibold text-gray-900">Search Stations</h2>
      <p className="text-xs text-gray-500">Enter coordinates or click on the map</p>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label htmlFor="lat" className="mb-1 block text-xs font-medium text-gray-700">
            Latitude ({COLOMBIA_BOUNDS.lat.min} to {COLOMBIA_BOUNDS.lat.max})
          </label>
          <input
            id="lat"
            type="number"
            step="0.0001"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            placeholder="e.g. 6.25"
            className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none ${
              lat && !latValid
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
        </div>
        <div>
          <label htmlFor="lon" className="mb-1 block text-xs font-medium text-gray-700">
            Longitude ({COLOMBIA_BOUNDS.lon.min} to {COLOMBIA_BOUNDS.lon.max})
          </label>
          <input
            id="lon"
            type="number"
            step="0.0001"
            value={lon}
            onChange={(e) => setLon(e.target.value)}
            placeholder="e.g. -75.57"
            className={`w-full rounded-md border px-3 py-2 text-sm focus:ring-2 focus:outline-none ${
              lon && !lonValid
                ? 'border-red-300 focus:ring-red-500'
                : 'border-gray-300 focus:ring-blue-500'
            }`}
          />
        </div>
      </div>

      <div>
        <label htmlFor="radius" className="mb-1 block text-xs font-medium text-gray-700">
          Radius (km)
        </label>
        <input
          id="radius"
          type="number"
          min="1"
          max="500"
          value={radius}
          onChange={(e) => setRadius(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      <button
        type="submit"
        disabled={!canSearch}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? 'Searching...' : 'Search'}
      </button>
    </form>
  );
}
