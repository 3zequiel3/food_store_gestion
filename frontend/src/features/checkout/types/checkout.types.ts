/**
 * Checkout types — domain types for the new checkout API (checkout-pay-first-flow).
 *
 * These types mirror the backend's CheckoutOnlineRequest, CheckoutPickupEfectivoRequest,
 * and response schemas. Created as part of the checkout-pay-first-flow change.
 */

/**
 * Payment method available at checkout.
 * Mirrors backend's FormaPago serialized via GET /api/v1/formas-pago.
 */
export interface PaymentMethodRead {
  codigo: string;
  descripcion: string;
  habilitada: boolean;
}

/**
 * Single line item for checkout request.
 * Mirrors backend's CheckoutItem schema.
 */
export interface CheckoutItem {
  producto_id: number;
  cantidad: number;
  personalizacion: number[] | null;
}

/**
 * Request payload for online checkout (with MercadoPago payment).
 * Mirrors backend's CheckoutOnlineRequest.
 */
export interface CheckoutOnlineRequest {
  items: CheckoutItem[];
  tipo_entrega: 'DELIVERY' | 'PICKUP';
  direccion_id: number | null;
  notas: string | null;
  
  // Payment fields (MercadoPago)
  card_token: string;
  payment_method_id: string;
  installments: number;
  idempotency_key: string; // UUID4
  identification_type: string;
  identification_number: string;
}

/**
 * Request payload for pickup+efectivo checkout (no online payment).
 * Mirrors backend's CheckoutPickupEfectivoRequest.
 */
export interface CheckoutPickupEfectivoRequest {
  items: CheckoutItem[];
  notas: string | null;
  // Note: no direccion_id, no payment fields
}

/**
 * Response for successful online checkout.
 * Mirrors backend's CheckoutOnlineResponse.
 */
export interface CheckoutOnlineResponse {
  pedido_id: number;
  pago_id: number;
  mp_status: string;
  mp_id: string;
  status_detail: string;
}

/**
 * Response for successful pickup+efectivo checkout.
 * Mirrors backend's CheckoutPickupEfectivoResponse.
 */
export interface CheckoutPickupEfectivoResponse {
  pedido_id: number;
}

/**
 * Error response for checkout failures.
 * Mirrors backend's CheckoutErrorResponse.
 */
export interface CheckoutErrorResponse {
  code: string;
  detail: string;
  mp_status?: string;
  status_detail?: string;
}

/**
 * Legacy types — DEPRECATED.
 * These are kept for backward compatibility during migration.
 * Remove after checkout-pay-first-flow is fully merged.
 */
/** @deprecated Use CheckoutItem instead */
export interface ItemPedidoPayload {
  producto_id: number;
  cantidad: number;
  personalizacion: number[] | null;
}

/** @deprecated Use CheckoutOnlineRequest or CheckoutPickupEfectivoRequest instead */
export interface CrearPedidoRequest {
  items: ItemPedidoPayload[];
  forma_pago_codigo: string;
  direccion_id: number | null;
  notas: string | null;
}

/** @deprecated Use CheckoutOnlineResponse or CheckoutPickupEfectivoResponse instead */
export interface PedidoRead {
  id: number;
  estado_codigo: string;
  total: string;
  creado_en: string;
}
