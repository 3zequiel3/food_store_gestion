import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { useCreateProduct } from '../../hooks/useCreateProduct';
import { useUpdateProduct } from '../../hooks/useUpdateProduct';
import type { ProductoRead } from '../../types/products.types';

interface ProductFormModalProps {
  producto?: ProductoRead;
  onClose: () => void;
}

interface FormErrors {
  nombre?: string;
  precio?: string;
  stock_cantidad?: string;
  imagen_url?: string;
}

export function ProductFormModal({ producto, onClose }: ProductFormModalProps) {
  const isEdit = !!producto;

  const [nombre, setNombre] = useState(producto?.nombre ?? '');
  const [descripcion, setDescripcion] = useState(producto?.descripcion ?? '');
  const [precio, setPrecio] = useState(producto ? String(producto.precio) : '');
  const [stock, setStock] = useState(producto ? String(producto.stock_cantidad) : '0');
  const [disponible, setDisponible] = useState(producto?.disponible ?? true);
  const [imagenUrl, setImagenUrl] = useState(producto?.imagen_url ?? '');
  const [errors, setErrors] = useState<FormErrors>({});

  const createMutation = useCreateProduct(onClose);
  const updateMutation = useUpdateProduct(onClose);
  const isPending = createMutation.isPending || updateMutation.isPending;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (nombre.trim().length < 2) errs.nombre = 'Mínimo 2 caracteres';
    const precioNum = parseFloat(precio);
    if (isNaN(precioNum) || precioNum <= 0) errs.precio = 'Debe ser un número mayor a 0';
    const stockNum = parseInt(stock, 10);
    if (isNaN(stockNum) || stockNum < 0) errs.stock_cantidad = 'Debe ser un número mayor o igual a 0';
    if (imagenUrl.trim() && !/^https?:\/\/.+/.test(imagenUrl.trim())) {
      errs.imagen_url = 'Debe ser una URL válida (https://...)';
    }
    return errs;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    const payload = {
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      precio: parseFloat(precio),
      stock_cantidad: parseInt(stock, 10),
      disponible,
      imagen_url: imagenUrl.trim() || null,
    };

    if (isEdit) {
      updateMutation.mutate({ id: producto.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-lg p-6 shadow-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-foreground">
            {isEdit ? 'Editar producto' : 'Nuevo producto'}
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Nombre <span className="text-destructive">*</span>
            </label>
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              placeholder="Ej: Hamburguesa clásica"
            />
            {errors.nombre && <p className="text-xs text-destructive mt-1">{errors.nombre}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Descripción</label>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
              placeholder="Descripción opcional"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Precio <span className="text-destructive">*</span>
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={precio}
                onChange={(e) => setPrecio(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                placeholder="0.00"
              />
              {errors.precio && <p className="text-xs text-destructive mt-1">{errors.precio}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Stock</label>
              <input
                type="number"
                min="0"
                step="1"
                value={stock}
                onChange={(e) => setStock(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
              {errors.stock_cantidad && (
                <p className="text-xs text-destructive mt-1">{errors.stock_cantidad}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">URL de imagen</label>
            <input
              value={imagenUrl}
              onChange={(e) => setImagenUrl(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
              placeholder="https://..."
            />
            {errors.imagen_url && (
              <p className="text-xs text-destructive mt-1">{errors.imagen_url}</p>
            )}
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={disponible}
              onChange={(e) => setDisponible(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            <span className="text-sm text-foreground">Disponible para la venta</span>
          </label>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : isEdit ? 'Guardar cambios' : 'Crear producto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
