/**
 * Payment entity types
 */

export const FormaPago = {
  EFECTIVO: 'EFECTIVO',
  TARJETA: 'TARJETA',
  MERCADOPAGO: 'MERCADOPAGO',
} as const

export type FormaPagoType = (typeof FormaPago)[keyof typeof FormaPago]

export type PaymentStatus = 'PENDIENTE' | 'PROCESANDO' | 'APROBADO' | 'RECHAZADO'

export interface Payment {
  id: string
  orderId: string
  amount: number
  method: FormaPagoType
  status: PaymentStatus
  externalTransactionId?: string
  createdAt?: string
  updatedAt?: string
}

export interface PaymentStatusUpdate {
  status: PaymentStatus
  externalId?: string
  errorMessage?: string
}
