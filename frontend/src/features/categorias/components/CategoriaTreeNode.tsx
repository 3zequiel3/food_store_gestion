import { useState } from 'react';
import { ChevronDown, ChevronRight, Plus, Pencil, Trash2 } from 'lucide-react';
import type { CategoriaTreeNode as CategoriaTreeNodeType } from '../types/categorias.types';

interface Props {
  node: CategoriaTreeNodeType;
  level: number;
  onAddChild: (parentId: number) => void;
  onEdit: (node: CategoriaTreeNodeType) => void;
  onDelete: (node: CategoriaTreeNodeType) => void;
}

export function CategoriaTreeNode({ node, level, onAddChild, onEdit, onDelete }: Props) {
  const hasChildren = node.subcategorias.length > 0;
  const [expanded, setExpanded] = useState(true);

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 group"
        style={{ paddingLeft: `${8 + level * 20}px` }}
      >
        <button
          type="button"
          onClick={() => setExpanded((p) => !p)}
          className="w-5 h-5 flex items-center justify-center text-gray-400 flex-shrink-0"
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )
          ) : (
            <span className="w-4 h-4 flex items-center justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
            </span>
          )}
        </button>

        <span className="flex-1 text-sm text-gray-700">{node.nombre}</span>

        {!hasChildren && (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded hidden group-hover:inline-flex">
            hoja
          </span>
        )}

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            type="button"
            onClick={() => onAddChild(node.id)}
            title="Agregar subcategoría"
            className="p-1 text-gray-400 hover:text-orange-500 hover:bg-orange-50 rounded transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onEdit(node)}
            title="Editar"
            className="p-1 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded transition-colors"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(node)}
            title="Eliminar"
            className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {hasChildren && expanded && (
        <div>
          {node.subcategorias.map((child) => (
            <CategoriaTreeNode
              key={child.id}
              node={child}
              level={level + 1}
              onAddChild={onAddChild}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
