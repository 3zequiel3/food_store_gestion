import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import type { EstadoCodigo } from '../types/orders.types';

const ESTADOS: { value: EstadoCodigo | ''; label: string }[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'CONFIRMADO', label: 'Confirmado' },
  { value: 'EN_PREPARACION', label: 'En preparación' },
  { value: 'EN_CAMINO', label: 'En camino' },
  { value: 'ENTREGADO', label: 'Entregado' },
  { value: 'CANCELADO', label: 'Cancelado' },
];

export function OrderFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const estado = searchParams.get('estado') ?? '';
  const desde = searchParams.get('desde') ?? '';
  const hasta = searchParams.get('hasta') ?? '';
  const q = searchParams.get('q') ?? '';

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      if (value) {
        updated.set(key, value);
      } else {
        updated.delete(key);
      }
      updated.delete('page');
      return updated;
    });
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-4 shadow-sm">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Filtros
      </h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por id o cliente…"
            value={q}
            onChange={(e) => setParam('q', e.target.value)}
            className="w-full rounded-lg border border-glass-border bg-glass backdrop-blur-sm py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-150"
          />
        </div>

        <select
          value={estado}
          onChange={(e) => setParam('estado', e.target.value)}
          className="rounded-lg border border-glass-border bg-glass backdrop-blur-sm px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-150"
        >
          {ESTADOS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={desde}
          onChange={(e) => setParam('desde', e.target.value)}
          className="rounded-lg border border-glass-border bg-glass backdrop-blur-sm px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-150"
          aria-label="Desde"
        />

        <input
          type="date"
          value={hasta}
          onChange={(e) => setParam('hasta', e.target.value)}
          className="rounded-lg border border-glass-border bg-glass backdrop-blur-sm px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-150"
          aria-label="Hasta"
        />
      </div>
    </div>
  );
}
