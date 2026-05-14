import { useState, useRef, useEffect } from 'react';
import { Search, X, AlertTriangle } from 'lucide-react';
import { useTodosIngredientes } from '../hooks/useTodosIngredientes';
import type { IngredienteAsignado } from '../types/ingredientes.types';

interface Props {
  value: IngredienteAsignado[];
  onChange: (items: IngredienteAsignado[]) => void;
}

export function IngredientAssignSelector({ value, onChange }: Props) {
  const { data: todos = [], isLoading, isError } = useTodosIngredientes();
  const [search, setSearch] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const assignedIds = new Set(value.map((v) => v.id));

  const filtered = todos.filter(
    (i) =>
      !assignedIds.has(i.id) &&
      i.nombre.toLowerCase().includes(search.toLowerCase()),
  );

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function add(id: number) {
    const ing = todos.find((i) => i.id === id);
    if (!ing) return;
    onChange([...value, { id: ing.id, nombre: ing.nombre, es_alergeno: ing.es_alergeno, es_removible: ing.es_removible }]);
    setSearch('');
    setDropdownOpen(false);
  }

  function remove(id: number) {
    onChange(value.filter((v) => v.id !== id));
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar ingrediente para agregar…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setDropdownOpen(true);
            }}
            onFocus={() => setDropdownOpen(true)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          />
        </div>

        {dropdownOpen && (
          <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {isLoading ? (
              <p className="text-sm text-gray-500 p-3">Cargando…</p>
            ) : isError ? (
              <p className="text-sm text-red-400 p-3">Error al cargar ingredientes</p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-gray-400 p-3">
                {search ? 'Sin resultados' : 'Todos los ingredientes ya fueron asignados'}
              </p>
            ) : (
              filtered.map((ing) => (
                <button
                  key={ing.id}
                  type="button"
                  onClick={() => add(ing.id)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center gap-2"
                >
                  <span>{ing.nombre}</span>
                  {ing.es_alergeno && (
                    <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {value.length > 0 && (
        <div className="border border-gray-200 rounded-lg divide-y divide-gray-100">
          {value.map((ing) => (
            <div key={ing.id} className="flex items-center gap-2 px-3 py-2">
              <span className="flex-1 text-sm text-gray-700">{ing.nombre}</span>

              {ing.es_alergeno && (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded-full flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Alérgeno
                </span>
              )}

              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  ing.es_removible
                    ? 'bg-blue-50 text-blue-600'
                    : 'bg-gray-50 text-gray-400'
                }`}
                title={ing.es_removible ? 'Removible por el cliente' : 'No removible'}
              >
                {ing.es_removible ? 'Removible' : 'Fijo'}
              </span>

              <button
                type="button"
                onClick={() => remove(ing.id)}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
