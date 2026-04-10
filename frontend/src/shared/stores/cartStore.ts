import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface CartItem {
  productId: string
  name: string
  price: number
  quantity: number
  image?: string
}

interface CartState {
  items: CartItem[]
  addItem: (item: CartItem) => void
  removeItem: (productId: string) => void
  updateQuantity: (productId: string, quantity: number) => void
  clearCart: () => void
  subtotal: number
  total: number
  itemCount: number
}

export const cartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      subtotal: 0,
      total: 0,
      itemCount: 0,

      addItem: (item: CartItem) => {
        set((state) => {
          const existingItem = state.items.find((i) => i.productId === item.productId)
          let newItems: CartItem[]

          if (existingItem) {
            newItems = state.items.map((i) =>
              i.productId === item.productId
                ? { ...i, quantity: i.quantity + item.quantity }
                : i
            )
          } else {
            newItems = [...state.items, item]
          }

          const itemCount = newItems.reduce((sum, i) => sum + i.quantity, 0)
          const subtotal = newItems.reduce((sum, i) => sum + i.price * i.quantity, 0)

          return { items: newItems, itemCount, subtotal, total: subtotal }
        })
      },

      removeItem: (productId: string) => {
        set((state) => {
          const newItems = state.items.filter((i) => i.productId !== productId)
          const itemCount = newItems.reduce((sum, i) => sum + i.quantity, 0)
          const subtotal = newItems.reduce((sum, i) => sum + i.price * i.quantity, 0)

          return { items: newItems, itemCount, subtotal, total: subtotal }
        })
      },

      updateQuantity: (productId: string, quantity: number) => {
        set((state) => {
          if (quantity <= 0) {
            return get().removeItem(productId) as unknown as CartState
          }

          const newItems = state.items.map((i) =>
            i.productId === productId ? { ...i, quantity } : i
          )
          const itemCount = newItems.reduce((sum, i) => sum + i.quantity, 0)
          const subtotal = newItems.reduce((sum, i) => sum + i.price * i.quantity, 0)

          return { items: newItems, itemCount, subtotal, total: subtotal }
        })
      },

      clearCart: () => {
        set({ items: [], itemCount: 0, subtotal: 0, total: 0 })
      },
    }),
    {
      name: 'cart-storage',
      partialize: (state) => ({
        items: state.items,
        itemCount: state.itemCount,
        subtotal: state.subtotal,
        total: state.total,
      }),
    }
  )
)
