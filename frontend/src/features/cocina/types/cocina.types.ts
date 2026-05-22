/**
 * Tipos del Kitchen Display System (KDS).
 *
 * Matchean los schemas de Pydantic del backend:
 * - IngredienteInfo
 * - CocinaPedidoItem
 * - CocinaPedidoResponse
 */

export type CocinaEstado = 'CONFIRMADO' | 'EN_PREPARACION';

/**
 * Minimal ingredient info in the kitchen order item payload.
 * Matches backend IngredienteInfo (D10).
 */
export interface IngredienteInfo {
  id: number;
  nombre: string;
  es_removible: boolean;
}

export interface CocinaPedidoItem {
  producto_id: number;
  nombre_snapshot: string;
  cantidad: number;
  personalizacion: number[] | null;
  notas: string | null;
  /** Full ingredient list with names (D10 — avoids "Ingrediente #N" raw IDs). */
  ingredientes: IngredienteInfo[];
  /** Exclusion IDs resolved to names by the backend (D10). */
  exclusiones_nombres: string[];
}

export interface CocinaPedidoResponse {
  id: number;
  estado: CocinaEstado;
  items: CocinaPedidoItem[];
  notas: string | null;
  cocina_entry_at: string; // ISO 8601 datetime
}

export type CocinaEventType =
  | 'pedido_confirmado'
  | 'pedido_en_preparacion'
  | 'pedido_terminado'
  | 'pedido_cancelado';

export interface CocinaWebSocketEvent {
  type: CocinaEventType;
  payload: CocinaPedidoResponse;
}
