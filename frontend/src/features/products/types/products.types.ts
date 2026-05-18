/**
 * Tipos del dominio productos (frontend).
 * Espejean los schemas del backend (backend/features/products/schemas.py).
 * Campos en snake_case para mantener fidelidad al contrato JSON.
 */

/** Categoría asociada a un producto (lectura) */
export interface CategoriaRead {
  id: number;
  nombre: string;
  padre_id: number | null;
}

/** Imagen de producto (lectura) */
export interface ImagenRead {
  id: number;
  url: string;
  orden: number;
  es_primaria: boolean;
}

/** Ingrediente asociado a un producto (lectura) */
export interface IngredienteAsociadoRead {
  id: number;
  nombre: string;
  /** Si el ingrediente es un alérgeno declarado */
  es_alergeno: boolean;
  /** Si el cliente puede solicitar que se retire el ingrediente */
  es_removible: boolean;
}

/** Producto simplificado para listado/grid */
export interface ProductoRead {
  id: number;
  nombre: string;
  descripcion: string | null;
  precio: number;
  imagen_url: string | null;
  disponible: boolean;
  stock_cantidad: number;
  categoria_id: number | null;
  imagenes: ImagenRead[];
  creado_en?: string;
}

/** Producto completo para la página de detalle */
export interface ProductoDetail extends ProductoRead {
  categorias: CategoriaRead[];
  ingredientes: IngredienteAsociadoRead[];
  imagenes: ImagenRead[];
}

/** Respuesta paginada de la lista de productos */
export interface PaginatedProductos {
  items: ProductoRead[];
  total: number;
  page: number;
  limit: number;
}

/**
 * Filtros del catálogo.
 * Todos los campos son opcionales — se omiten del request si no están definidos.
 */
export interface ProductFilters {
  page?: number;
  limit?: number;
  search?: string;
  categoria_id?: number;
  disponible?: boolean;
  excluir_alergenos?: boolean;
  excluir_alergeno_ids?: number[];
}

/** Payload para crear un producto (admin) */
export interface ProductoCreate {
  nombre: string;
  descripcion?: string | null;
  precio: number;
  stock_cantidad?: number;
  disponible?: boolean;
  imagen_url?: string | null;
  categoria_ids: number[];
  ingrediente_ids?: { ingrediente_id: number; es_removible: boolean }[];
}

/** Payload para editar un producto — todos los campos opcionales (admin) */
export interface ProductoUpdate {
  nombre?: string;
  descripcion?: string | null;
  precio?: number;
  stock_cantidad?: number;
  disponible?: boolean;
  imagen_url?: string | null;
}

/** Payload para actualizar stock absoluto (admin) */
export interface StockUpdate {
  stock_cantidad: number;
}
