/**
 * Order entity types
 */

import type { Product } from '../product'

export const EstadoPedido = {
  PENDIENTE: 'PENDIENTE',
  CONFIRMADO: 'CONFIRMADO',
  PREPARACION: 'PREPARACION',
  LISTO: 'LISTO',
  ENTREGADO: 'ENTREGADO',
  CANCELADO: 'CANCELADO',
} as const

export type EstadoPedidoType = (typeof EstadoPedido)[keyof typeof EstadoPedido]

export interface OrderItem {
  productId: string
  product?: Product
  quantity: number
  price: number
  subtotal: number
}

export interface Order {
  id: string
  userId: string
  items: OrderItem[]
  total: number
  status: EstadoPedidoType
  paymentMethod: string
  shippingAddress?: string
  notes?: string
  createdAt?: string
  updatedAt?: string
}

export interface OrderState {
  orders: Order[]
  currentOrder: Order | null
}
