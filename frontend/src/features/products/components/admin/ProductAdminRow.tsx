import { Pencil, Trash2, Loader2 } from 'lucide-react';
import { useToggleDisponibilidad } from '../../hooks/useToggleDisponibilidad';
import type { ProductoRead } from '../../types/products.types';

interface ProductAdminRowProps {
  product: ProductoRead;
  onEdit: (product: ProductoRead) => void;
  onDelete: (product: ProductoRead) => void;
}

export function ProductAdminRow({ product, onEdit, onDelete }: ProductAdminRowProps) {
  const toggleMutation = useToggleDisponibilidad();

  return (
    <tr className="border-t border-border hover:bg-muted/30 transition-colors">
      {/* Thumbnail */}
      <td className="px-4 py-3 w-12">
        <div className="h-10 w-10 rounded-lg bg-muted overflow-hidden flex-shrink-0">
          {product.imagen_url ? (
            <img
              src={product.imagen_url}
              alt={product.nombre}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center text-muted-foreground/30 text-lg">
              🍽
            </div>
          )}
        </div>
      </td>

      {/* Nombre + descripción */}
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-foreground truncate max-w-[200px]">{product.nombre}</p>
        {product.descripcion && (
          <p className="text-xs text-muted-foreground truncate max-w-[200px]">{product.descripcion}</p>
        )}
      </td>

      {/* Precio */}
      <td className="px-4 py-3 text-sm text-foreground whitespace-nowrap">
        ${Number(product.precio).toLocaleString('es-AR', { minimumFractionDigits: 2 })}
      </td>

      {/* Stock */}
      <td className="px-4 py-3 text-sm text-foreground">
        <span className={product.stock_cantidad === 0 ? 'text-destructive font-medium' : ''}>
          {product.stock_cantidad}
        </span>
      </td>

      {/* Disponibilidad — clickeable para toggle */}
      <td className="px-4 py-3">
        <button
          type="button"
          onClick={() => toggleMutation.mutate(product.id)}
          disabled={toggleMutation.isPending}
          title="Click para cambiar disponibilidad"
          className="inline-flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {toggleMutation.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          ) : null}
          <span className={`
            inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium cursor-pointer
            ${product.disponible
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
            }
          `}>
            {product.disponible ? 'Disponible' : 'Inactivo'}
          </span>
        </button>
      </td>

      {/* Acciones */}
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-1">
          <button
            type="button"
            onClick={() => onEdit(product)}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            title="Editar"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(product)}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
            title="Eliminar"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}
