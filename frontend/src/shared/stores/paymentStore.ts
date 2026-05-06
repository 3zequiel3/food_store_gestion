import { create } from 'zustand'

export type CheckoutStep = 'idle' | 'address' | 'method' | 'processing' | 'result'
export type PaymentStatus = 'pending' | 'processing' | 'approved' | 'rejected' | 'error'

interface PaymentState {
  pedidoId: number | null
  checkoutStep: CheckoutStep
  preferenceId: string | null
  paymentStatus: PaymentStatus
  error: string | null

  /**
   * Begin a checkout flow for a given `pedidoId`.
   * Sets step to `'address'` and status to `'pending'`.
   */
  startCheckout: (pedidoId: number) => void

  /** Store the MercadoPago preference id returned by the backend. */
  setPreference: (preferenceId: string) => void

  /** Advance the payment status (driven by MP webhook / callback). */
  updatePaymentStatus: (status: PaymentStatus) => void

  /** Reset everything to the initial state (after success, error recovery, or cancel). */
  resetPayment: () => void
}

const initialState: Pick<
  PaymentState,
  'pedidoId' | 'checkoutStep' | 'preferenceId' | 'paymentStatus' | 'error'
> = {
  pedidoId: null,
  checkoutStep: 'idle',
  preferenceId: null,
  paymentStatus: 'pending',
  error: null,
}

/**
 * Payment / checkout flow store.
 *
 * NOT persisted intentionally — checkout state is transient.
 * Rehydrating `paymentStatus = 'processing'` after a page refresh
 * would leave the checkout in a broken state. (US-000e, design.md §Decisión 4)
 */
export const usePaymentStore = create<PaymentState>()((set) => ({
  ...initialState,

  startCheckout: (pedidoId) => {
    set({ ...initialState, pedidoId, checkoutStep: 'address', paymentStatus: 'pending' })
  },

  setPreference: (preferenceId) => {
    set({ preferenceId })
  },

  updatePaymentStatus: (status) => {
    set({ paymentStatus: status })
  },

  resetPayment: () => {
    set({ ...initialState })
  },
}))

// ---------------------------------------------------------------------------
// Atomic selectors
// ---------------------------------------------------------------------------

export const selectCheckoutStep = (s: PaymentState) => s.checkoutStep
export const selectPaymentStatus = (s: PaymentState) => s.paymentStatus
export const selectPreferenceId = (s: PaymentState) => s.preferenceId
export const selectPaymentError = (s: PaymentState) => s.error
