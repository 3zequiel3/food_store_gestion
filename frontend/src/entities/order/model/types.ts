/**
 * Order / cart domain types.
 *
 * Naming convention:
 * - `CartItem` stays in English by spec mandate (Integrador.txt:256).
 *   There is no `Carrito` table in the backend (RN-CR01 — cart is client-side only).
 * - Field names use snake_case to match the backend Producto DTO shape
 *   (`producto_id`, `imagen_url`) since values come from server responses.
 * - `Personalizacion` uses snake_case (`ingredientes_excluidos`) because the backend
 *   will receive this structure in the future `DetallePedido.personalizacion` field.
 */

export interface Personalizacion {
  /** IDs of ingredients to exclude from this item (RN-CR05). */
  ingredientes_excluidos: number[]
}

export interface CartItem {
  producto_id: number
  nombre: string
  precio: number
  cantidad: number
  imagen_url?: string
  personalizacion: Personalizacion
}
