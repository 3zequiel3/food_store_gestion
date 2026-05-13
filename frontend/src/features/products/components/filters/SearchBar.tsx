import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, X } from 'lucide-react';

export function SearchBar() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialValue = searchParams.get('search') ?? '';
  const [value, setValue] = useState(initialValue);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const urlSearch = searchParams.get('search') ?? '';
    if (urlSearch !== value) {
      setValue(urlSearch);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value;
    setValue(next);

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        if (next) {
          updated.set('search', next);
        } else {
          updated.delete('search');
        }
        updated.set('page', '1');
        return updated;
      });
    }, 300);
  }

  function handleClear() {
    setValue('');
    if (timerRef.current) clearTimeout(timerRef.current);
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      updated.delete('search');
      updated.set('page', '1');
      return updated;
    });
  }

  return (
    <div className="relative flex items-center">
      <Search className="absolute left-3 h-4 w-4 text-muted-foreground pointer-events-none" />
      <input
        type="text"
        value={value}
        onChange={handleChange}
        placeholder="Buscar productos..."
        aria-label="Buscar productos"
        className="w-full pl-9 pr-9 py-2.5 rounded-lg border border-glass-border bg-glass backdrop-blur-sm text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-150"
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          aria-label="Limpiar búsqueda"
          className="absolute right-2 flex items-center justify-center h-5 w-5 rounded-sm text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
