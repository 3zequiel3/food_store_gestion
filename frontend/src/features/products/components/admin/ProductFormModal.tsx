import { useEffect, useState, useCallback, useRef } from 'react';
import { X, Loader2, Upload, Link as LinkIcon, Star, Trash2, Image as ImageIcon } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useCreateProduct } from '../../hooks/useCreateProduct';
import { useUpdateProduct } from '../../hooks/useUpdateProduct';
import type { ProductoRead, ImagenRead, ProductoDetail } from '../../types/products.types';
import type { IngredienteAsignado } from '../../../ingredientes/types/ingredientes.types';
import { CategoryLeafSelector } from '../../../categorias/components/CategoryLeafSelector';
import { IngredientAssignSelector } from '../../../ingredientes/components/IngredientAssignSelector';
import { diffIngredientes } from '../../../ingredientes/utils/diff-ingredientes';
import {
  uploadProductImage,
  addProductImageUrl,
  deleteProductImage,
  setProductImagePrimary,
  addProductIngredient,
  removeProductIngredient,
} from '../../services/admin-products.service';
import { getProduct } from '../../services/products.service';
import { toast } from 'sonner';

interface ProductFormModalProps {
  producto?: ProductoRead;
  onClose: () => void;
}

interface FormErrors {
  nombre?: string;
  precio?: string;
  stock_cantidad?: string;
  categoria_ids?: string;
  ingredientes?: string;
  imagen_url?: string;
}

type ImageMode = 'file' | 'url';
const MAX_IMAGE_SIZE_MB = 2;
const MAX_IMAGE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

/** Returns true if valid, false + toast if rejected */
function validateImageFile(file: File): boolean {
  if (file.size > MAX_IMAGE_BYTES) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
    toast.error(`"${file.name}" pesa ${sizeMB} MB (máximo ${MAX_IMAGE_SIZE_MB} MB)`);
    return false;
  }
  return true;
}

export function ProductFormModal({ producto, onClose }: ProductFormModalProps) {
  const isEdit = !!producto;

  // Basic fields
  const [nombre, setNombre] = useState(producto?.nombre ?? '');
  const [descripcion, setDescripcion] = useState(producto?.descripcion ?? '');
  const [precio, setPrecio] = useState(producto ? String(producto.precio) : '');
  const [stock, setStock] = useState(producto ? String(producto.stock_cantidad) : '0');
  const [disponible, setDisponible] = useState(producto?.disponible ?? true);

  // Categories
  const [categoriaIds, setCategoriaIds] = useState<number[]>([]);

  // Ingredients
  const [ingredientes, setIngredientes] = useState<IngredienteAsignado[]>([]);
  const originalIngredientes = useRef<IngredienteAsignado[]>([]);

  // Images
  const [imagenes, setImagenes] = useState<ImagenRead[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // Pending files for create mode (uploaded after product is created)
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const pendingFilesRef = useRef<File[]>([]);

  // Keep ref in sync with state
  useEffect(() => {
    pendingFilesRef.current = pendingFiles;
  }, [pendingFiles]);

  const [imageMode, setImageMode] = useState<ImageMode>('file');
  const [imageUrl, setImageUrl] = useState('');
  const [imageUrlError, setImageUrlError] = useState('');
  const [uploading, setUploading] = useState(false);

  // Form errors
  const [errors, setErrors] = useState<FormErrors>({});

  const createMutation = useCreateProduct((createdProduct) => {
    // After product is created, upload any pending files then close
    const files = pendingFilesRef.current;
    if (files.length > 0) {
      console.log('[Create] Producto creado, subiendo', files.length, 'imagen(es)');
      uploadPendingFiles(createdProduct.id, files).finally(() => {
        onClose();
      });
    } else {
      onClose();
    }
  });

  // In edit mode: sync ingredients after basic fields update, then close
  const handleUpdateSuccess = useCallback(async () => {
    if (!producto) return;
    try {
      await syncIngredientes(producto.id, originalIngredientes.current, ingredientes);
    } catch (err) {
      console.error('[IngredientSync] Error:', err);
      toast.error('Error al sincronizar ingredientes');
    }
    onClose();
  }, [producto, ingredientes, onClose]);

  const updateMutation = useUpdateProduct(handleUpdateSuccess);
  const isPending = createMutation.isPending || updateMutation.isPending;
  const isLoadingDetail = isEdit && detailLoading;

  // Load full product detail when editing (the list row only has ProductoRead, not categorias/ingredientes)
  useEffect(() => {
    if (!producto) {
      // Reset for create mode
      setCategoriaIds([]);
      setIngredientes([]);
      originalIngredientes.current = [];
      setImagenes([]);
      setPendingFiles([]);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    getProduct(producto.id)
      .then((detail: ProductoDetail) => {
        if (cancelled) return;
        setCategoriaIds(detail.categorias?.map((c) => c.id) ?? []);
        const loadedIngredientes = detail.ingredientes?.map((ing) => ({
          id: ing.id,
          nombre: ing.nombre,
          es_alergeno: ing.es_alergeno,
          es_removible: ing.es_removible,
        })) ?? [];
        setIngredientes(loadedIngredientes);
        originalIngredientes.current = loadedIngredientes;
        setImagenes(detail.imagenes ?? []);
      })
      .catch(() => {
        toast.error('No se pudo cargar el detalle del producto');
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });

    return () => { cancelled = true; };
  }, [producto]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const queryClient = useQueryClient();

  // Upload pending files after product creation
  const uploadPendingFiles = async (productId: number, files: File[]) => {
    setUploading(true);
    for (const file of files) {
      try {
        console.log('[Upload] Subiendo imagen:', file.name);
        await uploadProductImage(productId, file);
        console.log('[Upload] OK:', file.name);
        toast.success(`"${file.name}" subida`);
      } catch (err: any) {
        console.error('[Upload] Error fatal:', err);
        const status = err.response?.status;
        if (status === 401) {
          toast.error('Sesión expirada. Logueate de nuevo para subir imágenes.');
        } else {
          toast.error(`Error al subir ${file.name}: ${err.message || 'Desconocido'}`);
        }
      }
    }
    // Refresh images from server after uploads
    if (files.length > 0) {
      try {
        const detail = await getProduct(productId);
        setImagenes(detail.imagenes ?? []);
        console.log('[Upload] Imágenes refrescadas:', detail.imagenes?.length);
      } catch {
        // Non-critical
      }
    }
    setPendingFiles([]);
    setUploading(false);
  };

  /**
   * Sync ingredient associations between original (loaded from backend) and current (form state).
   * Strategy: DELETE removed, POST added, DELETE→POST for es_removible changes (backend reactivates soft-deleted pivots).
   */
  async function syncIngredientes(
    productoId: number,
    original: IngredienteAsignado[],
    current: IngredienteAsignado[],
  ): Promise<void> {
    const changes = diffIngredientes(original, current);

    for (const change of changes) {
      if (change.type === 'remove') {
        await removeProductIngredient(productoId, change.ingrediente.id);
      } else if (change.type === 'add') {
        await addProductIngredient(productoId, change.ingrediente.id, change.ingrediente.es_removible);
      } else if (change.type === 'update') {
        // DELETE first (soft-deletes the pivot), then POST (reactivates with new es_removible)
        await removeProductIngredient(productoId, change.after.id);
        await addProductIngredient(productoId, change.after.id, change.after.es_removible);
      }
    }
  }

  // Handle file selection/add to pending (create mode) or upload immediately (edit mode)
  const handleFileAdd = useCallback((file: File) => {
    if (!validateImageFile(file)) return;

    if (isEdit) {
      // Edit mode: upload via backend (handles storage + DB registration)
      setUploading(true);
      console.log('[Upload] Edit mode. Subiendo:', file.name);
      uploadProductImage(producto!.id, file)
        .then(() => {
          console.log('[Upload] OK:', file.name);
          toast.success('Imagen subida');
          // Refresh images from server
          return getProduct(producto!.id);
        })
        .then((detail) => {
          setImagenes(detail.imagenes ?? []);
        })
        .catch((err: any) => {
          console.error('[Upload] Error en edición:', err);
          const status = err.response?.status;
          if (status === 401) {
            toast.error('Sesión expirada. Logueate de nuevo.');
          } else {
            toast.error('Error al subir la imagen');
          }
        })
        .finally(() => setUploading(false));
    } else {
      // Create mode: queue file for upload after creation
      setPendingFiles((prev) => [...prev, file]);
      toast.success(`"${file.name}" lista para subir`);
    }
  }, [isEdit, producto]);

  // Handle drag and drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    for (const file of Array.from(files)) {
      if (file.type.startsWith('image/')) {
        handleFileAdd(file);
      }
    }
  }, [handleFileAdd]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  // Handle file input
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      for (const file of Array.from(files)) {
        if (file.type.startsWith('image/')) {
          handleFileAdd(file);
        }
      }
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  }, [handleFileAdd]);

  // Handle URL add
  const handleAddUrl = useCallback(async () => {
    if (!imageUrl.trim()) return;
    if (!/^https?:\/\/.+/.test(imageUrl.trim())) {
      setImageUrlError('Debe ser una URL válida (https://...)');
      return;
    }
    setImageUrlError('');

    if (isEdit) {
      // Edit mode: upload immediately
      setUploading(true);
      try {
        const result = await addProductImageUrl(producto!.id, imageUrl.trim());
        setImagenes((prev) => [...prev, result]);
        setImageUrl('');
        toast.success('Imagen agregada');
      } catch {
        toast.error('Error al agregar la imagen');
      } finally {
        setUploading(false);
      }
    }
    // Create mode: URL is included in the payload via getInitialImageUrl
  }, [imageUrl, isEdit, producto]);

  // For create mode: URL-based initial image
  const getInitialImageUrl = useCallback(() => {
    if (!isEdit && imageUrl.trim() && /^https?:\/\/.+/.test(imageUrl.trim())) {
      return imageUrl.trim();
    }
    return null;
  }, [isEdit, imageUrl]);

  // Set primary image
  const handleSetPrimary = useCallback(async (imagenId: number) => {
    if (!producto) return;
    try {
      await setProductImagePrimary(producto.id, imagenId);
      setImagenes((prev) =>
        prev.map((img) => ({
          ...img,
          es_primaria: img.id === imagenId,
        }))
      );
    } catch {
      toast.error('Error al establecer imagen primaria');
    }
  }, [producto]);

  // Delete image
  const handleDeleteImage = useCallback(async (imagenId: number) => {
    if (!producto) return;
    try {
      await deleteProductImage(producto.id, imagenId);
      setImagenes((prev) => prev.filter((img) => img.id !== imagenId));
    } catch {
      toast.error('Error al eliminar la imagen');
    }
  }, [producto]);

  function validate(): FormErrors {
    const errs: FormErrors = {};
    if (nombre.trim().length < 2) errs.nombre = 'Mínimo 2 caracteres';
    const precioNum = parseFloat(precio);
    if (isNaN(precioNum) || precioNum <= 0) errs.precio = 'Debe ser un número mayor a 0';
    const stockNum = parseInt(stock, 10);
    if (isNaN(stockNum) || stockNum < 0) errs.stock_cantidad = 'Debe ser un número mayor o igual a 0';
    if (categoriaIds.length === 0) errs.categoria_ids = 'El producto debe tener al menos una categoría';
    if (ingredientes.length === 0) errs.ingredientes = 'El producto debe tener al menos un ingrediente';
    return errs;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    const initialImageUrl = getInitialImageUrl();

    const payload = {
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      precio: parseFloat(precio),
      stock_cantidad: parseInt(stock, 10),
      disponible,
      categoria_ids: categoriaIds,
      ingrediente_ids: ingredientes.map((ing) => ({
        ingrediente_id: ing.id,
        es_removible: ing.es_removible,
      })),
      imagen_url: initialImageUrl,
    };

    if (isEdit) {
      // Edit mode: update basic fields first; ingredient sync runs in updateMutation.onSuccess
      updateMutation.mutate({ id: producto.id, payload: {
        nombre: payload.nombre,
        descripcion: payload.descripcion,
        precio: payload.precio,
        stock_cantidad: payload.stock_cantidad,
        disponible: payload.disponible,
      }});
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
        className="bg-card border border-border rounded-lg w-full max-w-4xl p-6 shadow-lg max-h-[90vh] overflow-y-auto relative"
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

        <form onSubmit={handleSubmit} className={isLoadingDetail ? 'opacity-50 pointer-events-none' : ''}>
          {/* Loading overlay for edit mode */}
          {isLoadingDetail && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/10 rounded-lg">
              <div className="flex items-center gap-2 text-sm text-foreground bg-card px-4 py-2 rounded-lg shadow">
                <Loader2 className="h-4 w-4 animate-spin" />
                Cargando datos del producto...
              </div>
            </div>
          )}
          {/* 2-column layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* LEFT COLUMN — data fields */}
            <div className="space-y-4">
              {/* Nombre */}
              <div>
                <label htmlFor="nombre" className="block text-sm font-medium text-foreground mb-1">
                  Nombre <span className="text-destructive">*</span>
                </label>
                <input
                  id="nombre"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  placeholder="Ej: Hamburguesa clásica"
                />
                {errors.nombre && <p className="text-xs text-destructive mt-1">{errors.nombre}</p>}
              </div>

              {/* Descripción */}
              <div>
                <label htmlFor="descripcion" className="block text-sm font-medium text-foreground mb-1">Descripción</label>
                <textarea
                  id="descripcion"
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                  placeholder="Descripción opcional"
                />
              </div>

              {/* Precio + Stock */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="precio" className="block text-sm font-medium text-foreground mb-1">
                    Precio <span className="text-destructive">*</span>
                  </label>
                  <input
                    id="precio"
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
                  <label htmlFor="stock" className="block text-sm font-medium text-foreground mb-1">Stock</label>
                  <input
                    id="stock"
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

              {/* Disponible */}
              <label htmlFor="disponible" className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  id="disponible"
                  type="checkbox"
                  checked={disponible}
                  onChange={(e) => setDisponible(e.target.checked)}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                <span className="text-sm text-foreground">Disponible para la venta</span>
              </label>

              {/* Categorías */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Categorías <span className="text-destructive">*</span>
                </label>
                <CategoryLeafSelector value={categoriaIds} onChange={setCategoriaIds} />
                {errors.categoria_ids && (
                  <p className="text-xs text-destructive mt-1">{errors.categoria_ids}</p>
                )}
              </div>

              {/* Ingredientes */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Ingredientes <span className="text-destructive">*</span>
                </label>
                <IngredientAssignSelector value={ingredientes} onChange={setIngredientes} />
                {errors.ingredientes && (
                  <p className="text-xs text-destructive mt-1">{errors.ingredientes}</p>
                )}
              </div>
            </div>

            {/* RIGHT COLUMN — image management */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">Gestión de imágenes</h3>

              {/* Mode toggle */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setImageMode('file')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
                    imageMode === 'file'
                      ? 'bg-primary/10 border-primary text-primary'
                      : 'border-border text-muted-foreground hover:bg-accent'
                  }`}
                >
                  <Upload className="h-4 w-4" />
                  Subir archivo
                </button>
                <button
                  type="button"
                  onClick={() => setImageMode('url')}
                  className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
                    imageMode === 'url'
                      ? 'bg-primary/10 border-primary text-primary'
                      : 'border-border text-muted-foreground hover:bg-accent'
                  }`}
                >
                  <LinkIcon className="h-4 w-4" />
                  Agregar URL
                </button>
              </div>

              {/* File upload zone */}
              {imageMode === 'file' && (
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary/40 transition-colors cursor-pointer"
                  onClick={() => document.getElementById('image-file-input')?.click()}
                >
                  <ImageIcon className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">
                    {isEdit
                      ? 'Arrastrá una imagen aquí o hacé click para seleccionar'
                      : 'Arrastrá una imagen aquí o hacé click para seleccionar (se subirá al crear el producto)'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Máximo {MAX_IMAGE_SIZE_MB} MB por imagen
                  </p>
                  <input
                    id="image-file-input"
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={handleFileInput}
                  />
                </div>
              )}

              {/* Pending files list (create mode) */}
              {pendingFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Imágenes pendientes de subir ({pendingFiles.length})
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {pendingFiles.map((file, i) => (
                      <div
                        key={i}
                        className="relative group aspect-square rounded-lg overflow-hidden border border-border bg-muted"
                      >
                        <img
                          src={URL.createObjectURL(file)}
                          alt={file.name}
                          className="w-full h-full object-cover"
                        />
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingFiles((prev) => prev.filter((_, idx) => idx !== i));
                          }}
                          className="absolute top-1 right-1 p-1 bg-white/90 rounded-full hover:bg-white transition-colors"
                          title="Quitar imagen"
                        >
                          <Trash2 className="h-3 w-3 text-red-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* URL input */}
              {imageMode === 'url' && (
                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      value={imageUrl}
                      onChange={(e) => { setImageUrl(e.target.value); setImageUrlError(''); }}
                      className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                      placeholder={isEdit ? 'https://...' : 'https://... (se agregará al crear el producto)'}
                    />
                    {imageUrlError && (
                      <p className="text-xs text-destructive mt-1">{imageUrlError}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={handleAddUrl}
                    disabled={uploading || !imageUrl.trim()}
                    className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    Confirmar
                  </button>
                </div>
              )}

              {/* Thumbnail list */}
              {imagenes.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    Imágenes del producto ({imagenes.length})
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {imagenes.map((img) => (
                      <div
                        key={img.id}
                        className="relative group aspect-square rounded-lg overflow-hidden border border-border"
                      >
                        <img
                          src={img.url}
                          alt={`Imagen ${img.orden + 1}`}
                          className="w-full h-full object-cover"
                        />
                        {/* Primary badge */}
                        {img.es_primaria && (
                          <span className="absolute top-1 left-1 bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
                            <Star className="h-3 w-3 fill-current" />
                            Primaria
                          </span>
                        )}
                        {/* Actions overlay */}
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                          {!img.es_primaria && (
                            <button
                              type="button"
                              onClick={() => handleSetPrimary(img.id)}
                              className="p-1.5 bg-white/90 rounded-full hover:bg-white transition-colors"
                              title="Establecer como primaria"
                            >
                              <Star className="h-4 w-4 text-yellow-500" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDeleteImage(img.id)}
                            className="p-1.5 bg-white/90 rounded-full hover:bg-white transition-colors"
                            title="Eliminar imagen"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {uploading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Subiendo imagen...
                </div>
              )}
            </div>
          </div>

          {/* Footer buttons */}
          <div className="flex gap-3 pt-4 mt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending || isLoadingDetail}
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
