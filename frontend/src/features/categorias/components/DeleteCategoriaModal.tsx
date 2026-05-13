import { Loader2, Trash2 } from 'lucide-react';
import { useDeleteCategoria } from '../hooks/useDeleteCategoria';
import type { CategoriaTreeNode } from '../types/categorias.types';

interface Props {
  categoria: CategoriaTreeNode;
  onClose: () => void;
}

export function DeleteCategoriaModal({ categoria, onClose }: Props) {
  const deleteMutation = useDeleteCategoria(onClose);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <div className="flex flex-col items-center text-center gap-3">
          <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
            <Trash2 className="w-6 h-6 text-red-500" />
          </div>
          <h2 className="text-lg font-semibold text-gray-800">Eliminar categoría</h2>
          <p className="text-sm text-gray-500">
            ¿Seguro que querés eliminar{' '}
            <span className="font-medium text-gray-700">{categoria.nombre}</span>? Esta acción no
            se puede deshacer.
          </p>
          {categoria.subcategorias.length > 0 && (
            <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 w-full">
              Esta categoría tiene {categoria.subcategorias.length} subcategoría
              {categoria.subcategorias.length > 1 ? 's' : ''}. Eliminá primero las subcategorías.
            </p>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => deleteMutation.mutate(categoria.id)}
            disabled={deleteMutation.isPending || categoria.subcategorias.length > 0}
            className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 disabled:bg-red-300 text-white rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {deleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Eliminar
          </button>
        </div>
      </div>
    </div>
  );
}
