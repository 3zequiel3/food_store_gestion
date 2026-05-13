import { Pencil, Trash2, AlertTriangle } from 'lucide-react';
import type { IngredienteRead } from '../types/ingredientes.types';

interface Props {
  ingrediente: IngredienteRead;
  onEdit: (ingrediente: IngredienteRead) => void;
  onDelete: (ingrediente: IngredienteRead) => void;
}

export function IngredienteRow({ ingrediente, onEdit, onDelete }: Props) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
      <td className="px-4 py-3 text-sm text-gray-700">{ingrediente.nombre}</td>
      <td className="px-4 py-3">
        {ingrediente.es_alergeno ? (
          <span className="inline-flex items-center gap-1 text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
            <AlertTriangle className="w-3 h-3" />
            Alérgeno
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2 justify-end">
          <button
            type="button"
            onClick={() => onEdit(ingrediente)}
            className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
            title="Editar"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(ingrediente)}
            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="Eliminar"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
