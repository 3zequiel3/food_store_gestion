import { useState } from 'react';
import { Plus, FolderTree, Loader2 } from 'lucide-react';
import { useCategorias } from '../../features/categorias/hooks/useCategorias';
import { CategoriaTreeNode } from '../../features/categorias/components/CategoriaTreeNode';
import { CategoriaFormModal } from '../../features/categorias/components/CategoriaFormModal';
import { DeleteCategoriaModal } from '../../features/categorias/components/DeleteCategoriaModal';
import type { CategoriaTreeNode as CategoriaTreeNodeType } from '../../features/categorias/types/categorias.types';

export function AdminCategoriasPage() {
  const { data: tree = [], isLoading, isError } = useCategorias();

  const [createModal, setCreateModal] = useState<{ parentId?: number } | null>(null);
  const [editCategoria, setEditCategoria] = useState<CategoriaTreeNodeType | null>(null);
  const [deleteCategoria, setDeleteCategoria] = useState<CategoriaTreeNodeType | null>(null);

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center">
              <FolderTree className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Categorías</h1>
              <p className="text-sm text-gray-500">Árbol de categorías del catálogo</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setCreateModal({})}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nueva categoría raíz
          </button>
        </div>

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
            </div>
          ) : isError ? (
            <div className="py-12 text-center text-sm text-red-500">Error al cargar categorías</div>
          ) : tree.length === 0 ? (
            <div className="py-16 text-center">
              <FolderTree className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No hay categorías todavía</p>
              <button
                type="button"
                onClick={() => setCreateModal({})}
                className="mt-3 text-sm text-orange-500 hover:text-orange-600 font-medium"
              >
                Crear la primera
              </button>
            </div>
          ) : (
            <div className="py-2">
              {tree.map((node) => (
                <CategoriaTreeNode
                  key={node.id}
                  node={node}
                  level={0}
                  onAddChild={(parentId) => setCreateModal({ parentId })}
                  onEdit={(n) => setEditCategoria(n)}
                  onDelete={(n) => setDeleteCategoria(n)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {createModal && (
        <CategoriaFormModal
          defaultPadreId={createModal.parentId ?? null}
          onClose={() => setCreateModal(null)}
        />
      )}

      {editCategoria && (
        <CategoriaFormModal
          categoria={editCategoria}
          onClose={() => setEditCategoria(null)}
        />
      )}

      {deleteCategoria && (
        <DeleteCategoriaModal
          categoria={deleteCategoria}
          onClose={() => setDeleteCategoria(null)}
        />
      )}
    </div>
  );
}
