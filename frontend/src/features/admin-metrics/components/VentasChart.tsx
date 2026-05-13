import { useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import type { Granularidad, MetricsDateFilter } from '../types/admin-metrics.types';
import { useVentasPorPeriodo } from '../hooks/useVentasPorPeriodo';

interface VentasChartProps {
  filter: MetricsDateFilter;
}

const GRANULARIDADES: { value: Granularidad; label: string }[] = [
  { value: 'dia', label: 'Por día' },
  { value: 'semana', label: 'Por semana' },
  { value: 'mes', label: 'Por mes' },
];

export function VentasChart({ filter }: VentasChartProps) {
  const [granularidad, setGranularidad] = useState<Granularidad>('dia');
  const { data, isLoading } = useVentasPorPeriodo(filter, granularidad);

  const chartData = data?.puntos.map((p) => ({
    periodo: p.periodo,
    ventas: parseFloat(p.total_ventas),
    pedidos: p.cantidad_pedidos,
  })) ?? [];

  return (
    <div className="bg-card border border-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">Evolución de ventas</h3>
        <select
          value={granularidad}
          onChange={(e) => setGranularidad(e.target.value as Granularidad)}
          className="text-xs px-2 py-1 border border-border rounded bg-background text-foreground focus:outline-none"
        >
          {GRANULARIDADES.map((g) => (
            <option key={g.value} value={g.value}>{g.label}</option>
          ))}
        </select>
      </div>

      {isLoading && <div className="h-64 bg-muted rounded animate-pulse" />}

      {!isLoading && chartData.length === 0 && (
        <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
          Sin datos para el periodo
        </div>
      )}

      {!isLoading && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="periodo" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value: number) => [`$${value.toFixed(2)}`, 'Ventas']}
            />
            <Line type="monotone" dataKey="ventas" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
