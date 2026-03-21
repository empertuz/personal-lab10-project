import type { StationResponse } from '../../types/index.ts';
import { StationCard } from './StationCard.tsx';

interface StationListProps {
  stations: StationResponse[];
  count: number;
  radiusKm: number;
  selectedStationId: string | null;
  onStationClick: (stationId: string) => void;
  onBack: () => void;
}

export function StationList({
  stations,
  count,
  radiusKm,
  selectedStationId,
  onStationClick,
  onBack,
}: StationListProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 p-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">
            {count} station{count !== 1 ? 's' : ''} found
          </h2>
          <p className="text-xs text-gray-500">Within {radiusKm} km radius</p>
        </div>
        <button
          onClick={onBack}
          className="rounded-md px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          ← New search
        </button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {stations.map((station) => (
          <StationCard
            key={station.id}
            station={station}
            isSelected={station.id === selectedStationId}
            onClick={() => onStationClick(station.id)}
          />
        ))}
      </div>
    </div>
  );
}
