import { useSearchParams } from 'react-router-dom';

export function DateRangeFilter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const desde = searchParams.get('desde') ?? '';
  const hasta = searchParams.get('hasta') ?? '';

  function update(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      return next;
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      <span className="text-sm text-muted-foreground">Periodo:</span>
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground">Desde</label>
        <input
          type="date"
          value={desde}
          onChange={(e) => update('desde', e.target.value)}
          className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground">Hasta</label>
        <input
          type="date"
          value={hasta}
          onChange={(e) => update('hasta', e.target.value)}
          className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </div>
      {(desde || hasta) && (
        <button
          onClick={() => setSearchParams({})}
          className="text-xs text-muted-foreground hover:text-foreground underline"
        >
          Limpiar
        </button>
      )}
    </div>
  );
}
