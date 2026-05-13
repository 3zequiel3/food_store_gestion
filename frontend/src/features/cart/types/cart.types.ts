/**
 * Tipos del dominio cart (frontend-only, sin contraparte backend directa).
 * Campos en snake_case para espejear el shape del DTO de Producto.
 * Doc: docs/frontend-architecture.md §4 (features frontend-only)
 */

export interface CartItem {
  producto_id: number;
  nombre: string;
  precio: number;
  cantidad: number;
  imagen_url?: string;
  /** Texto libre de personalizacion (ej: "sin cebolla") */
  personalizacion?: string;
  /** IDs de ingredientes excluidos (para enviar al backend) */
  personalizacionIds?: number[];
}
