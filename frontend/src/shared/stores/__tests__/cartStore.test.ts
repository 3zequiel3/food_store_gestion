import { describe, it, expect, beforeEach } from 'vitest'
import { useCartStore } from '../cartStore'
import {
  selectItems,
  selectTotalItems,
  selectTotalPrice,
  selectGetItem,
} from '../cartStore'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const productA = { producto_id: 1, nombre: 'Pizza Margherita', precio: 100, imagen_url: 'pizza.jpg' }
const productB = { producto_id: 2, nombre: 'Empanada', precio: 50 }

const noPersonalizacion = { ingredientes_excluidos: [] }
const conPersonalizacion = { ingredientes_excluidos: [3, 7] }

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useCartStore', () => {
  beforeEach(() => {
    // Clear jsdom localStorage and reset in-memory state before every test.
    localStorage.clear()
    useCartStore.setState({ items: [] })
  })

  // ---- addItem -------------------------------------------------------------

  it('addItem creates a new entry when producto_id is not in cart', () => {
    useCartStore.getState().addItem(productA, 2, noPersonalizacion)
    const items = useCartStore.getState().items
    expect(items).toHaveLength(1)
    expect(items[0].producto_id).toBe(1)
    expect(items[0].cantidad).toBe(2)
    expect(items[0].nombre).toBe('Pizza Margherita')
    expect(items[0].precio).toBe(100)
    expect(items[0].imagen_url).toBe('pizza.jpg')
  })

  it('addItem increments cantidad when producto_id already exists (RN-CR03)', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    useCartStore.getState().addItem(productA, 3, noPersonalizacion)
    const items = useCartStore.getState().items
    expect(items).toHaveLength(1)
    expect(items[0].cantidad).toBe(4)
  })

  it('addItem stores personalizacion per item (RN-CR05)', () => {
    useCartStore.getState().addItem(productA, 1, conPersonalizacion)
    const item = useCartStore.getState().items[0]
    expect(item.personalizacion.ingredientes_excluidos).toEqual([3, 7])
  })

  it('addItem can hold multiple distinct products', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    useCartStore.getState().addItem(productB, 2, noPersonalizacion)
    expect(useCartStore.getState().items).toHaveLength(2)
  })

  // ---- removeItem ----------------------------------------------------------

  it('removeItem removes the item by producto_id', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    useCartStore.getState().addItem(productB, 1, noPersonalizacion)
    useCartStore.getState().removeItem(1)
    const items = useCartStore.getState().items
    expect(items).toHaveLength(1)
    expect(items[0].producto_id).toBe(2)
  })

  it('removeItem does nothing if producto_id is not in cart', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    useCartStore.getState().removeItem(999)
    expect(useCartStore.getState().items).toHaveLength(1)
  })

  // ---- updateQuantity ------------------------------------------------------

  it('updateQuantity changes the quantity of an existing item', () => {
    useCartStore.getState().addItem(productA, 2, noPersonalizacion)
    useCartStore.getState().updateQuantity(1, 5)
    expect(useCartStore.getState().items[0].cantidad).toBe(5)
  })

  it('updateQuantity with 0 removes the item', () => {
    useCartStore.getState().addItem(productA, 2, noPersonalizacion)
    useCartStore.getState().updateQuantity(1, 0)
    expect(useCartStore.getState().items).toHaveLength(0)
  })

  it('updateQuantity with negative value removes the item', () => {
    useCartStore.getState().addItem(productA, 2, noPersonalizacion)
    useCartStore.getState().updateQuantity(1, -1)
    expect(useCartStore.getState().items).toHaveLength(0)
  })

  // ---- clearCart -----------------------------------------------------------

  it('clearCart empties all items', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    useCartStore.getState().addItem(productB, 2, noPersonalizacion)
    useCartStore.getState().clearCart()
    expect(useCartStore.getState().items).toHaveLength(0)
  })

  // ---- selectors -----------------------------------------------------------

  it('selectItems returns the items array', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    expect(selectItems(useCartStore.getState())).toHaveLength(1)
  })

  it('selectTotalItems sums cantidad across all items', () => {
    useCartStore.getState().addItem(productA, 3, noPersonalizacion)
    useCartStore.getState().addItem(productB, 2, noPersonalizacion)
    expect(selectTotalItems(useCartStore.getState())).toBe(5)
  })

  it('selectTotalItems returns 0 for empty cart', () => {
    expect(selectTotalItems(useCartStore.getState())).toBe(0)
  })

  it('selectTotalPrice sums precio * cantidad per item', () => {
    // productA: 100 * 2 = 200, productB: 50 * 3 = 150 → total 350
    useCartStore.getState().addItem(productA, 2, noPersonalizacion)
    useCartStore.getState().addItem(productB, 3, noPersonalizacion)
    expect(selectTotalPrice(useCartStore.getState())).toBe(350)
  })

  it('selectTotalPrice returns 0 for empty cart', () => {
    expect(selectTotalPrice(useCartStore.getState())).toBe(0)
  })

  it('selectGetItem returns the item for a known producto_id', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)
    const item = selectGetItem(1)(useCartStore.getState())
    expect(item).toBeDefined()
    expect(item?.nombre).toBe('Pizza Margherita')
  })

  it('selectGetItem returns undefined for unknown producto_id', () => {
    expect(selectGetItem(999)(useCartStore.getState())).toBeUndefined()
  })

  // ---- persistence ---------------------------------------------------------

  it('persist: addItem writes to localStorage under food-store-cart', () => {
    useCartStore.getState().addItem(productA, 1, noPersonalizacion)

    const raw = localStorage.getItem('food-store-cart')
    expect(raw).not.toBeNull()
    const stored = JSON.parse(raw!)
    expect(stored.state.items).toHaveLength(1)
    expect(stored.state.items[0].producto_id).toBe(1)
  })

  it('persist: personalizacion (ingredientes_excluidos) survives rehydrate', async () => {
    // Reset state FIRST (triggers a persist write that clears old data)
    useCartStore.setState({ items: [] })

    // Write stored data AFTER setState so persist doesn't overwrite it
    const stored = JSON.stringify({
      state: {
        items: [
          {
            producto_id: 1,
            nombre: 'Pizza',
            precio: 100,
            cantidad: 1,
            personalizacion: { ingredientes_excluidos: [3, 7] },
          },
        ],
      },
      version: 0,
    })
    localStorage.setItem('food-store-cart', stored)

    await new Promise<void>((resolve) => {
      const unsub = useCartStore.persist.onFinishHydration(() => {
        unsub()
        resolve()
      })
      useCartStore.persist.rehydrate()
    })

    const item = useCartStore.getState().items[0]
    expect(item).toBeDefined()
    expect(item.personalizacion.ingredientes_excluidos).toEqual([3, 7])
  })
})
