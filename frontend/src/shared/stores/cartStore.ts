import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CartItem, Personalizacion } from '../../entities/order/model'

/** Minimal product info required to build a CartItem (comes from the catalog DTO). */
interface ProductoRef {
  producto_id: number
  nombre: string
  precio: number
  imagen_url?: string
}

interface CartState {
  /** Cart line items. Persisted in full (RN-CR02). */
  items: CartItem[]

  /**
   * Add a product to the cart.
   * - If `producto_id` already exists, increments `cantidad` (RN-CR03).
   * - If new, appends a fresh `CartItem` with the given `personalizacion`.
   */
  addItem: (producto: ProductoRef, cantidad: number, personalizacion: Personalizacion) => void

  /** Remove an item by `producto_id`. */
  removeItem: (producto_id: number) => void

  /**
   * Set the quantity for an item.
   * If `cantidad <= 0`, the item is removed entirely.
   */
  updateQuantity: (producto_id: number, cantidad: number) => void

  /** Empty the cart. Called from checkout success flow, NEVER from logout. */
  clearCart: () => void
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: (producto, cantidad, personalizacion) => {
        set((state) => {
          const existing = state.items.find((i) => i.producto_id === producto.producto_id)
          if (existing) {
            // RN-CR03: increment quantity, do not duplicate
            return {
              items: state.items.map((i) =>
                i.producto_id === producto.producto_id
                  ? { ...i, cantidad: i.cantidad + cantidad }
                  : i
              ),
            }
          }
          // New item — build the flat CartItem shape (Integrador.txt:256)
          const newItem: CartItem = {
            producto_id: producto.producto_id,
            nombre: producto.nombre,
            precio: producto.precio,
            cantidad,
            imagen_url: producto.imagen_url,
            personalizacion,
          }
          return { items: [...state.items, newItem] }
        })
      },

      removeItem: (producto_id) => {
        set((state) => ({
          items: state.items.filter((i) => i.producto_id !== producto_id),
        }))
      },

      updateQuantity: (producto_id, cantidad) => {
        if (cantidad <= 0) {
          get().removeItem(producto_id)
          return
        }
        set((state) => ({
          items: state.items.map((i) =>
            i.producto_id === producto_id ? { ...i, cantidad } : i
          ),
        }))
      },

      clearCart: () => {
        set({ items: [] })
      },
    }),
    {
      name: 'food-store-cart',
      // RN-CR02: persist everything — the cart must survive refresh, close, and logout.
      partialize: (state) => ({ items: state.items }),
    }
  )
)

// ---------------------------------------------------------------------------
// Atomic selectors
// ---------------------------------------------------------------------------

export const selectItems = (s: CartState) => s.items

/** Total number of units across all cart items. */
export const selectTotalItems = (s: CartState) =>
  s.items.reduce((sum, i) => sum + i.cantidad, 0)

/** Sum of precio * cantidad for all items (uses flat CartItem shape). */
export const selectTotalPrice = (s: CartState) =>
  s.items.reduce((sum, i) => sum + i.precio * i.cantidad, 0)

/** Returns the CartItem for a given `producto_id`, or `undefined` if not in cart. */
export const selectGetItem = (producto_id: number) => (s: CartState) =>
  s.items.find((i) => i.producto_id === producto_id)
