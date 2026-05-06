import { describe, it, expect, beforeEach } from 'vitest'
import { usePaymentStore } from '../paymentStore'
import {
  selectCheckoutStep,
  selectPaymentStatus,
  selectPreferenceId,
  selectPaymentError,
} from '../paymentStore'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('usePaymentStore', () => {
  beforeEach(() => {
    localStorage.clear()
    usePaymentStore.setState({
      pedidoId: null,
      checkoutStep: 'idle',
      preferenceId: null,
      paymentStatus: 'pending',
      error: null,
    })
  })

  // ---- initial state -------------------------------------------------------

  it('initial state is idle / pending / nulls', () => {
    const s = usePaymentStore.getState()
    expect(s.checkoutStep).toBe('idle')
    expect(s.paymentStatus).toBe('pending')
    expect(s.pedidoId).toBeNull()
    expect(s.preferenceId).toBeNull()
    expect(s.error).toBeNull()
  })

  // ---- startCheckout -------------------------------------------------------

  it('startCheckout records pedidoId and moves to address step', () => {
    usePaymentStore.getState().startCheckout(42)
    const s = usePaymentStore.getState()
    expect(s.pedidoId).toBe(42)
    expect(s.checkoutStep).toBe('address')
    expect(s.paymentStatus).toBe('pending')
    expect(s.error).toBeNull()
  })

  // ---- setPreference -------------------------------------------------------

  it('setPreference stores the MercadoPago preference id', () => {
    usePaymentStore.getState().startCheckout(1)
    usePaymentStore.getState().setPreference('mp-pref-abc123')
    expect(usePaymentStore.getState().preferenceId).toBe('mp-pref-abc123')
  })

  // ---- updatePaymentStatus -------------------------------------------------

  it('updatePaymentStatus transitions through valid statuses', () => {
    usePaymentStore.getState().startCheckout(1)
    usePaymentStore.getState().updatePaymentStatus('processing')
    expect(usePaymentStore.getState().paymentStatus).toBe('processing')

    usePaymentStore.getState().updatePaymentStatus('approved')
    expect(usePaymentStore.getState().paymentStatus).toBe('approved')

    usePaymentStore.getState().updatePaymentStatus('rejected')
    expect(usePaymentStore.getState().paymentStatus).toBe('rejected')

    usePaymentStore.getState().updatePaymentStatus('error')
    expect(usePaymentStore.getState().paymentStatus).toBe('error')
  })

  // ---- resetPayment --------------------------------------------------------

  it('resetPayment returns all fields to their initial values', () => {
    usePaymentStore.getState().startCheckout(5)
    usePaymentStore.getState().setPreference('pref-xyz')
    usePaymentStore.getState().updatePaymentStatus('approved')

    usePaymentStore.getState().resetPayment()

    const s = usePaymentStore.getState()
    expect(s.pedidoId).toBeNull()
    expect(s.checkoutStep).toBe('idle')
    expect(s.preferenceId).toBeNull()
    expect(s.paymentStatus).toBe('pending')
    expect(s.error).toBeNull()
  })

  // ---- selectors -----------------------------------------------------------

  it('atomic selectors read the correct slices', () => {
    usePaymentStore.getState().startCheckout(10)
    usePaymentStore.getState().setPreference('pref-sel')
    usePaymentStore.getState().updatePaymentStatus('processing')

    const s = usePaymentStore.getState()
    expect(selectCheckoutStep(s)).toBe('address')
    expect(selectPaymentStatus(s)).toBe('processing')
    expect(selectPreferenceId(s)).toBe('pref-sel')
    expect(selectPaymentError(s)).toBeNull()
  })

  // ---- NO persistence ------------------------------------------------------

  it('does NOT write to localStorage under food-store-payment after startCheckout', () => {
    usePaymentStore.getState().startCheckout(1)
    expect(localStorage.getItem('food-store-payment')).toBeNull()
  })

  it('does NOT write any food-store-payment key even after multiple actions', () => {
    usePaymentStore.getState().startCheckout(1)
    usePaymentStore.getState().setPreference('pref')
    usePaymentStore.getState().updatePaymentStatus('processing')
    usePaymentStore.getState().resetPayment()
    expect(localStorage.getItem('food-store-payment')).toBeNull()
  })
})
