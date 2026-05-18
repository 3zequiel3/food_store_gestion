import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  CheckoutItem,
  CheckoutOnlineRequest,
  CheckoutOnlineResponse,
  CheckoutPickupEfectivoRequest,
  CheckoutPickupEfectivoResponse,
} from '../types/checkout.types';

/**
 * Checkout service — new atomic pay-first flow.
 *
 * Replaces the old orders.service.ts and payments.service.ts for order creation.
 * The checkout endpoints create orders atomically with payment (online) or
 * without payment (pickup+efectivo).
 */

/**
 * Create an order with online payment via MercadoPago.
 * POST /api/v1/checkout/online
 *
 * The order is only created if MP returns approved status (strict mode).
 * Any other status throws an error without creating an order.
 *
 * @param payload - CheckoutOnlineRequest with payment details
 * @returns CheckoutOnlineResponse with order and payment IDs
 */
export async function createCheckoutOnline(
  payload: CheckoutOnlineRequest,
): Promise<CheckoutOnlineResponse> {
  const response = await apiClient.post<CheckoutOnlineResponse>(
    ENDPOINTS.checkout.online,
    payload,
  );
  return response.data;
}

/**
 * Create a pickup order with cash payment (no online payment).
 * POST /api/v1/checkout/pickup-efectivo
 *
 * The order is created directly in PENDIENTE state.
 *
 * @param payload - CheckoutPickupEfectivoRequest
 * @returns CheckoutPickupEfectivoResponse with order ID
 */
export async function createCheckoutPickupEfectivo(
  payload: CheckoutPickupEfectivoRequest,
): Promise<CheckoutPickupEfectivoResponse> {
  const response = await apiClient.post<CheckoutPickupEfectivoResponse>(
    ENDPOINTS.checkout.pickupEfectivo,
    payload,
  );
  return response.data;
}

/**
 * Helper to build a CheckoutItem from cart item.
 */
export function buildCheckoutItem(item: {
  producto_id: number;
  cantidad: number;
  personalizacion?: number[] | null;
}): CheckoutItem {
  return {
    producto_id: item.producto_id,
    cantidad: item.cantidad,
    personalizacion: item.personalizacion ?? null,
  };
}
