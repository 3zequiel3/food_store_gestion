import { useState } from 'react';
import { Plus, FlaskConical, Loader2, Search } from 'lucide-react';
import { useIngredientes } from '../../features/ingredientes/hooks/useIngredientes';
import { IngredienteRow } from '../../features/ingredientes/components/IngredienteRow';
import { IngredienteFormModal } from '../../features/ingredientes/components/IngredienteFormModal';
import { DeleteIngredienteModal } from '../../features/ingredientes/components/DeleteIngredienteModal';
import type { IngredienteRead } from '../../features/ingredientes/types/ingredientes.types';

const LIMIT = 20;

export function AdminIngredientesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const { data, isLoading, isError } = useIngredientes(page, LIMIT);

  const [showCreate, setShowCreate] = useState(false);
  const [editIngrediente, setEditIngrediente] = useState<IngredienteRead | null>(null);
  const [deleteIngrediente, setDeleteIngrediente] = useState<IngredienteRead | null>(null);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / LIMIT);

  const filteredItems = debouncedSearch
    ? items.filter((i) => i.nombre.toLowerCase().includes(debouncedSearch.toLowerCase()))
    : items;

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearch(e.target.value);
    setDebouncedSearch(e.target.value);
    setPage(1);
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center">
              <FlaskConical className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Ingredientes</h1>
              <p className="text-sm text-gray-500">{total} ingredientes en total</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nuevo ingrediente
          </button>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <div className="relative max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar ingrediente…"
                value={search}
                onChange={handleSearchChange}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            </div>
          ) : isError ? (
            <div className="py-12 text-center text-sm text-red-500">Error al cargar ingredientes</div>
          ) : filteredItems.length === 0 ? (
            <div className="py-12 text-center">
              <FlaskConical className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">
                {debouncedSearch ? 'Sin resultados para esa búsqueda' : 'No hay ingredientes todavía'}
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Nombre
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Alérgeno
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Removible
                  </th>
                  <th className="px-4 py-3 w-24" />
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((ing) => (
                  <IngredienteRow
                    key={ing.id}
                    ingrediente={ing}
                    onEdit={(i) => setEditIngrediente(i)}
                    onDelete={(i) => setDeleteIngrediente(i)}
                  />
                ))}
              </tbody>
            </table>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-sm text-gray-500">
                Página {page} de {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {showCreate && <IngredienteFormModal onClose={() => setShowCreate(false)} />}
      {editIngrediente && (
        <IngredienteFormModal
          ingrediente={editIngrediente}
          onClose={() => setEditIngrediente(null)}
        />
      )}
      {deleteIngrediente && (
        <DeleteIngredienteModal
          ingrediente={deleteIngrediente}
          onClose={() => setDeleteIngrediente(null)}
        />
      )}
    </div>
  );
}
