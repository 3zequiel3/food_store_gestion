import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { useCreateCategoria } from '../hooks/useCreateCategoria';
import { useUpdateCategoria } from '../hooks/useUpdateCategoria';
import { useCategorias } from '../hooks/useCategorias';
import { ApiError } from '../../../api/interceptors/error';
import type { CategoriaTreeNode } from '../types/categorias.types';

interface Props {
  categoria?: CategoriaTreeNode;
  defaultPadreId?: number | null;
  onClose: () => void;
}

function flattenTree(nodes: CategoriaTreeNode[], excludeId?: number): { id: number; nombre: string; depth: number }[] {
  return nodes.flatMap((n) => {
    if (n.id === excludeId) return [];
    return [
      { id: n.id, nombre: n.nombre, depth: 0 },
      ...flattenTree(n.subcategorias, excludeId).map((c) => ({ ...c, depth: c.depth + 1 })),
    ];
  });
}

export function CategoriaFormModal({ categoria, defaultPadreId, onClose }: Props) {
  const isEdit = !!categoria;
  const { data: tree = [] } = useCategorias();

  const [nombre, setNombre] = useState(categoria?.nombre ?? '');
  const [padreId, setPadreId] = useState<string>(
    categoria?.padre_id != null
      ? String(categoria.padre_id)
      : defaultPadreId != null
        ? String(defaultPadreId)
        : '',
  );
  const [error, setError] = useState('');

  const opciones = flattenTree(tree, isEdit ? categoria?.id : undefined);

  const createMutation = useCreateCategoria(onClose);
  const updateMutation = useUpdateCategoria(onClose);

  const isPending = createMutation.isPending || updateMutation.isPending;

  function validate(): boolean {
    if (!nombre.trim()) {
      setError('El nombre es obligatorio');
      return false;
    }
    setError('');
    return true;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const payload = {
      nombre: nombre.trim(),
      padre_id: padreId ? Number(padreId) : null,
    };

    if (isEdit) {
      updateMutation.mutate(
        { id: categoria!.id, payload },
        {
          onError(err) {
            if (err instanceof ApiError && err.status === 409) {
              setError('Ya existe una categoría con ese nombre en el mismo nivel');
            }
          },
        },
      );
    } else {
      createMutation.mutate(payload, {
        onError(err) {
          if (err instanceof ApiError && err.status === 409) {
            setError('Ya existe una categoría con ese nombre en el mismo nivel');
          }
        },
      });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? 'Editar categoría' : 'Nueva categoría'}
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
              placeholder="Ej: Bebidas"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
            />
            {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Categoría padre <span className="text-gray-400">(opcional)</span>
            </label>
            <select
              value={padreId}
              onChange={(e) => setPadreId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white"
            >
              <option value="">— Sin padre (categoría raíz) —</option>
              {opciones.map((o) => (
                <option key={o.id} value={o.id}>
                  {'  '.repeat(o.depth)}
                  {o.depth > 0 ? '└ ' : ''}
                  {o.nombre}
                </option>
              ))}
            </select>
          </div>

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
              {isEdit ? 'Guardar cambios' : 'Crear categoría'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
