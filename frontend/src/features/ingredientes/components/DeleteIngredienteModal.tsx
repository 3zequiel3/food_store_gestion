import { Loader2, Trash2 } from 'lucide-react';
import { useDeleteIngrediente } from '../hooks/useDeleteIngrediente';
import type { IngredienteRead } from '../types/ingredientes.types';

interface Props {
  ingrediente: IngredienteRead;
  onClose: () => void;
}

export function DeleteIngredienteModal({ ingrediente, onClose }: Props) {
  const deleteMutation = useDeleteIngrediente(onClose);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <div className="flex flex-col items-center text-center gap-3">
          <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
            <Trash2 className="w-6 h-6 text-red-500" />
          </div>
          <h2 className="text-lg font-semibold text-gray-800">Eliminar ingrediente</h2>
          <p className="text-sm text-gray-500">
            ¿Seguro que querés eliminar{' '}
            <span className="font-medium text-gray-700">{ingrediente.nombre}</span>? Si está
            asignado a algún producto, la operación fallará.
          </p>
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
            onClick={() => deleteMutation.mutate(ingrediente.id)}
            disabled={deleteMutation.isPending}
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
