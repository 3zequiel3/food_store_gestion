/**
 * Checkout types — domain types for the checkout flow.
 *
 * Mirrors the backend's CrearPedidoRequest and related types.
 * All monetary values are numbers (backend uses Decimal, but JSON converts to string;
 * the API client handles the conversion).
 */

/**
 * Single line item for the order payload.
 * Mirrors backend's ItemPedidoRequest.
 */
export interface ItemPedidoPayload {
  producto_id: number;
  cantidad: number;
  personalizacion: number[] | null;
}

/**
 * Request payload for creating a new order.
 * Mirrors backend's CrearPedidoRequest.
 */
export interface CrearPedidoRequest {
  items: ItemPedidoPayload[];
  forma_pago_codigo: string;
  direccion_id: number | null;
  notas: string | null;
}

/**
 * Payment method read from backend.
 * Mirrors backend's FormaPagoRead.
 */
export interface PaymentMethodRead {
  codigo: string;
  descripcion: string;
  habilitada: boolean;
}

/**
 * Order read response after creation.
 * Mirrors backend's PedidoRead.
 */
export interface PedidoRead {
  id: number;
  estado_codigo: string;
  total: string; // Decimal as string from backend
  creado_en: string; // ISO datetime string
}
