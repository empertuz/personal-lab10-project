import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { RainfallYearly } from '../../types/index.ts';

interface YearlyRainfallChartProps {
  data: RainfallYearly[];
}

interface TooltipPayloadItem {
  payload: RainfallYearly;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadItem[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-2 text-xs shadow-md">
      <p className="font-semibold text-gray-900">{d.year}</p>
      <p className="text-blue-600">Total: {d.total_mm.toFixed(1)} mm</p>
      <p className="text-gray-500">Rainy days: {d.rainy_days}</p>
      <p className="text-gray-500">Data days: {d.data_days}</p>
    </div>
  );
}

export function YearlyRainfallChart({ data }: YearlyRainfallChartProps) {
  if (data.length === 0) {
    return <p className="py-4 text-center text-xs text-gray-400">No data available</p>;
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -10 }}>
          <XAxis
            dataKey="year"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="total_mm" fill="#3b82f6" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
