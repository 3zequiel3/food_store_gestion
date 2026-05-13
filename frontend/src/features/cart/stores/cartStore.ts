import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { CartItem } from '../types/cart.types';

interface CartState {
  items: CartItem[];
}

interface CartActions {
  /**
   * Agrega un item al carrito.
   * Si ya existe un item con el mismo producto_id, incrementa cantidad.
   * D2: no toca authStore.
   */
  addItem(item: Omit<CartItem, 'cantidad'>, cantidad?: number): void;
  /** Remueve completamente un item del carrito */
  removeItem(producto_id: number): void;
  /**
   * Actualiza la cantidad de un item.
   * Si cantidad <= 0, remueve el item (spec req: updateQuantity a 0 → remove).
   */
  updateQuantity(producto_id: number, cantidad: number): void;
  /** Vacía el carrito completamente */
  clearCart(): void;
  /** Cantidad total de unidades en el carrito (suma de cantidades) */
  getTotalItems(): number;
  /** Precio total = sum(precio * cantidad) */
  getTotalPrice(): number;
}

type CartStore = CartState & CartActions;

/**
 * D2 — Store de carrito (frontend-only, persistido en localStorage).
 * Sobrevive al logout — clearSession() de authStore NO lo toca (RN verificado).
 * Storage key: food-store-cart.
 */
export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],

      addItem(item, cantidad = 1) {
        set((state) => {
          const existing = state.items.find(
            (i) => i.producto_id === item.producto_id,
          );
          if (existing) {
            return {
              items: state.items.map((i) =>
                i.producto_id === item.producto_id
                  ? { ...i, cantidad: i.cantidad + cantidad }
                  : i,
              ),
            };
          }
          return {
            items: [...state.items, { ...item, cantidad }],
          };
        });
      },

      removeItem(producto_id) {
        set((state) => ({
          items: state.items.filter((i) => i.producto_id !== producto_id),
        }));
      },

      updateQuantity(producto_id, cantidad) {
        if (cantidad <= 0) {
          get().removeItem(producto_id);
          return;
        }
        set((state) => ({
          items: state.items.map((i) =>
            i.producto_id === producto_id ? { ...i, cantidad } : i,
          ),
        }));
      },

      clearCart() {
        set({ items: [] });
      },

      getTotalItems() {
        return get().items.reduce((sum, item) => sum + item.cantidad, 0);
      },

      getTotalPrice() {
        return get().items.reduce(
          (sum, item) => sum + Number(item.precio) * item.cantidad,
          0,
        );
      },
    }),
    {
      name: 'food-store-cart',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ items: state.items }),
    },
  ),
);
