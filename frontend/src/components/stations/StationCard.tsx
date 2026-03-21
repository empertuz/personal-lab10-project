import type { StationResponse } from '../../types/index.ts';
import { formatDistance } from '../../utils/format.ts';

interface StationCardProps {
  station: StationResponse;
  isSelected?: boolean;
  onClick: () => void;
}

function statusColor(status: string | null): string {
  switch (status) {
    case 'Activa':
      return 'bg-green-100 text-green-700';
    case 'Suspendida':
      return 'bg-red-100 text-red-700';
    case 'En Mantenimiento':
      return 'bg-yellow-100 text-yellow-700';
    default:
      return 'bg-gray-100 text-gray-600';
  }
}

export function StationCard({ station, isSelected, onClick }: StationCardProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-lg border p-3 text-left transition-colors hover:bg-blue-50 focus:ring-2 focus:ring-blue-500 focus:outline-none ${
        isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900 leading-tight">
          {station.name ?? station.id}
        </h3>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColor(station.status)}`}
        >
          {station.status ?? 'Unknown'}
        </span>
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
        {station.department && <span>{station.department}</span>}
        <span>{formatDistance(station.distance_km)}</span>
        <span className={station.has_data ? 'text-green-600' : 'text-gray-400'}>
          {station.has_data ? 'Has data' : 'No data'}
        </span>
      </div>

      {station.data_summary && station.data_summary.total_records > 0 && (
        <p className="mt-1 text-[10px] text-gray-400">
          {station.data_summary.date_from} → {station.data_summary.date_to} ·{' '}
          {station.data_summary.total_records.toLocaleString()} records
        </p>
      )}
    </button>
  );
}
