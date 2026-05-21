/**
 * Tipos del Kitchen Display System (KDS).
 *
 * Matchean los schemas de Pydantic del backend:
 * - CocinaPedidoItem
 * - CocinaPedidoResponse
 */

export type CocinaEstado = 'CONFIRMADO' | 'EN_PREPARACION';

export interface CocinaPedidoItem {
  producto_id: number;
  nombre_snapshot: string;
  cantidad: number;
  personalizacion: number[] | null;
  notas: string | null;
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
