import { create } from 'zustand'

export type FormaPago = 'EFECTIVO' | 'TARJETA' | 'MERCADOPAGO'
export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed'

interface PaymentState {
  selectedMethod: FormaPago | null
  status: PaymentStatus
  externalId: string | null
  setMethod: (method: FormaPago) => void
  setStatus: (status: PaymentStatus) => void
  setExternalId: (id: string) => void
  reset: () => void
}

export const paymentStore = create<PaymentState>((set) => ({
  selectedMethod: null,
  status: 'pending',
  externalId: null,

  setMethod: (method: FormaPago) => {
    set({ selectedMethod: method })
  },

  setStatus: (status: PaymentStatus) => {
    set({ status })
  },

  setExternalId: (id: string) => {
    set({ externalId: id })
  },

  reset: () => {
    set({ selectedMethod: null, status: 'pending', externalId: null })
  },
}))
