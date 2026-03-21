import { useStationDetail } from '../../hooks/useStationDetail.ts';
import { LoadingSpinner } from '../common/LoadingSpinner.tsx';
import { ErrorMessage } from '../common/ErrorMessage.tsx';
import { YearlyRainfallChart } from '../charts/YearlyRainfallChart.tsx';
import { formatDate, formatNumber, formatPercent } from '../../utils/format.ts';

interface StationDetailProps {
  stationId: string;
  onBack: () => void;
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

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-2 text-xs">
      <span className="font-medium text-gray-500">{label}</span>
      <span className="text-right text-gray-900">{value}</span>
    </div>
  );
}

export function StationDetail({ stationId, onBack }: StationDetailProps) {
  const { station, stats, yearlyData, loading, error } = useStationDetail(stationId);

  if (loading) return <LoadingSpinner message="Loading station details..." />;
  if (error) return <ErrorMessage message={error} />;
  if (!station) return null;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 p-3">
        <button
          onClick={onBack}
          className="mb-2 rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        >
          ← Back to results
        </button>
        <div className="flex items-start justify-between gap-2">
          <h2 className="text-base font-semibold text-gray-900">{station.name ?? station.id}</h2>
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColor(station.status)}`}
          >
            {station.status ?? 'Unknown'}
          </span>
        </div>
        <p className="text-xs text-gray-500">ID: {station.id}</p>
      </div>

      {/* Content */}
      <div className="flex-1 space-y-4 overflow-y-auto p-3">
        {/* Metadata */}
        <section>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-gray-400 uppercase">
            Station Info
          </h3>
          <div className="space-y-1.5 rounded-lg bg-gray-50 p-3">
            <InfoRow label="Category" value={station.category} />
            <InfoRow label="Technology" value={station.technology} />
            <InfoRow
              label="Altitude"
              value={station.altitude != null ? `${station.altitude} m` : null}
            />
            <InfoRow
              label="Coordinates"
              value={
                station.latitude != null && station.longitude != null
                  ? `${station.latitude.toFixed(4)}, ${station.longitude.toFixed(4)}`
                  : null
              }
            />
            <InfoRow label="Department" value={station.department} />
            <InfoRow label="Municipality" value={station.municipality} />
            <InfoRow label="Operational Area" value={station.operational_area} />
            <InfoRow label="Stream" value={station.stream} />
            <InfoRow label="Hydro Area" value={station.hydro_area} />
            <InfoRow label="Hydro Zone" value={station.hydro_zone} />
            <InfoRow label="Hydro Subzone" value={station.hydro_subzone} />
            <InfoRow label="Installed" value={formatDate(station.installed_at)} />
            <InfoRow label="Suspended" value={formatDate(station.suspended_at)} />
          </div>
        </section>

        {/* Stats */}
        {stats && (
          <section>
            <h3 className="mb-2 text-xs font-semibold tracking-wide text-gray-400 uppercase">
              Rainfall Summary
            </h3>
            <div className="grid grid-cols-2 gap-2">
              <StatBox
                label="Date Range"
                value={`${formatDate(stats.date_from)} → ${formatDate(stats.date_to)}`}
              />
              <StatBox label="Total Records" value={stats.total_records.toLocaleString()} />
              <StatBox label="Avg (mm/day)" value={formatNumber(stats.avg_mm)} />
              <StatBox label="Max (mm/day)" value={formatNumber(stats.max_mm)} />
              <StatBox label="Min (mm/day)" value={formatNumber(stats.min_mm)} />
              <StatBox label="Coverage" value={formatPercent(stats.coverage_pct)} />
            </div>
          </section>
        )}

        {/* Chart */}
        {yearlyData.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold tracking-wide text-gray-400 uppercase">
              Yearly Rainfall Trend
            </h3>
            <YearlyRainfallChart data={yearlyData} />
          </section>
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 p-2.5">
      <p className="text-[10px] font-medium text-gray-400">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}
