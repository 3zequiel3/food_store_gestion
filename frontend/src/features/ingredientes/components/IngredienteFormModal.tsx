import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { useCreateIngrediente } from '../hooks/useCreateIngrediente';
import { useUpdateIngrediente } from '../hooks/useUpdateIngrediente';
import { ApiError } from '../../../api/interceptors/error';
import type { IngredienteRead } from '../types/ingredientes.types';

interface Props {
  ingrediente?: IngredienteRead;
  onClose: () => void;
}

export function IngredienteFormModal({ ingrediente, onClose }: Props) {
  const isEdit = !!ingrediente;

  const [nombre, setNombre] = useState(ingrediente?.nombre ?? '');
  const [esAlergeno, setEsAlergeno] = useState(ingrediente?.es_alergeno ?? false);
  const [esRemovible, setEsRemovible] = useState(ingrediente?.es_removible ?? false);
  const [error, setError] = useState('');

  const createMutation = useCreateIngrediente(onClose);
  const updateMutation = useUpdateIngrediente(onClose);
  const isPending = createMutation.isPending || updateMutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!nombre.trim()) {
      setError('El nombre es obligatorio');
      return;
    }
    setError('');

    const payload = { nombre: nombre.trim(), es_alergeno: esAlergeno, es_removible: esRemovible };

    const onError = (err: Error) => {
      if (err instanceof ApiError && err.status === 409) {
        setError('Ya existe un ingrediente con ese nombre');
      }
    };

    if (isEdit) {
      updateMutation.mutate({ id: ingrediente!.id, payload }, { onError });
    } else {
      createMutation.mutate(payload, { onError });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? 'Editar ingrediente' : 'Nuevo ingrediente'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej: Queso mozzarella"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
            {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={esAlergeno}
              onChange={(e) => setEsAlergeno(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 accent-orange-500"
            />
            <span className="text-sm text-gray-700">Es alérgeno</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={esRemovible}
              onChange={(e) => setEsRemovible(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 accent-orange-500"
            />
            <span className="text-sm text-gray-700">Es removible por el cliente</span>
          </label>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEdit ? 'Guardar cambios' : 'Crear ingrediente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
