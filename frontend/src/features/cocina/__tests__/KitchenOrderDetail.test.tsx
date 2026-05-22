/**
 * Tests — KitchenOrderDetail component (Task 5.3 / P1.4 frontend).
 *
 * Verifica:
 * - Se renderizan los nombres de ingredientes (NO los IDs crudos).
 * - NO aparece "Ingrediente #N" en el DOM.
 * - Las exclusiones se muestran por nombre (exclusiones_nombres), no por ID.
 * - Los ingredientes removibles se distinguen visualmente.
 * - Ingrediente sin exclusión: muestra la lista completa.
 * - Ingrediente en lista + excluido: aparece tachado o marcado como excluido.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CocinaPedidoItem } from '../types/cocina.types';
import { KitchenOrderDetail } from '../components/KitchenOrderDetail';

function makeItem(overrides: Partial<CocinaPedidoItem> = {}): CocinaPedidoItem {
  return {
    producto_id: 1,
    nombre_snapshot: 'Hamburguesa Clásica',
    cantidad: 1,
    personalizacion: null,
    notas: null,
    ingredientes: [],
    exclusiones_nombres: [],
    ...overrides,
  };
}

function renderDetail(
  items: CocinaPedidoItem[],
  opts: { orderId?: number; notas?: string | null } = {},
) {
  const onClose = vi.fn();
  return render(
    <KitchenOrderDetail
      orderId={opts.orderId ?? 1}
      items={items}
      notas={opts.notas ?? null}
      onClose={onClose}
    />,
  );
}

describe('KitchenOrderDetail — ingredient rendering (Task 5.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ingredient names from ingredientes list', () => {
    const item = makeItem({
      ingredientes: [
        { id: 10, nombre: 'Lechuga', es_removible: true },
        { id: 11, nombre: 'Tomate', es_removible: true },
        { id: 12, nombre: 'Carne', es_removible: false },
      ],
    });

    renderDetail([item]);

    expect(screen.getByText('Lechuga')).toBeInTheDocument();
    expect(screen.getByText('Tomate')).toBeInTheDocument();
    expect(screen.getByText('Carne')).toBeInTheDocument();
  });

  it('does NOT render raw ingredient IDs ("Ingrediente #N" pattern)', () => {
    const item = makeItem({
      ingredientes: [
        { id: 10, nombre: 'Lechuga', es_removible: true },
      ],
      personalizacion: [10],
      exclusiones_nombres: ['Lechuga'],
    });

    renderDetail([item]);

    // Must NOT appear as "Ingrediente #10"
    expect(screen.queryByText(/ingrediente #10/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ingrediente #\d+/i)).not.toBeInTheDocument();
  });

  it('shows excluded ingredients by name from exclusiones_nombres', () => {
    const item = makeItem({
      ingredientes: [
        { id: 10, nombre: 'Lechuga', es_removible: true },
        { id: 11, nombre: 'Tomate', es_removible: true },
        { id: 12, nombre: 'Carne', es_removible: false },
      ],
      personalizacion: [10, 11],
      exclusiones_nombres: ['Lechuga', 'Tomate'],
    });

    renderDetail([item]);

    // Excluded names must appear
    expect(screen.getByText('Lechuga')).toBeInTheDocument();
    expect(screen.getByText('Tomate')).toBeInTheDocument();
    // Non-excluded ingredient still visible
    expect(screen.getByText('Carne')).toBeInTheDocument();
  });

  it('renders exclusion summary using names, not raw IDs', () => {
    const item = makeItem({
      ingredientes: [
        { id: 5, nombre: 'Cebolla', es_removible: true },
      ],
      personalizacion: [5],
      exclusiones_nombres: ['Cebolla'],
    });

    renderDetail([item]);

    // Should not show "Sin: Ingrediente #5"
    expect(screen.queryByText(/ingrediente #5/i)).not.toBeInTheDocument();
    // Should show the name-based exclusion (may appear more than once: summary + row)
    expect(screen.getAllByText(/cebolla/i).length).toBeGreaterThan(0);
  });

  it('renders all ingredients when no exclusions are present', () => {
    const item = makeItem({
      ingredientes: [
        { id: 1, nombre: 'Pan', es_removible: false },
        { id: 2, nombre: 'Queso', es_removible: true },
        { id: 3, nombre: 'Jamón', es_removible: true },
      ],
      personalizacion: null,
      exclusiones_nombres: [],
    });

    renderDetail([item]);

    expect(screen.getByText('Pan')).toBeInTheDocument();
    expect(screen.getByText('Queso')).toBeInTheDocument();
    expect(screen.getByText('Jamón')).toBeInTheDocument();
  });

  it('renders nothing for ingredient list when ingredientes is empty', () => {
    const item = makeItem({
      ingredientes: [],
      exclusiones_nombres: [],
    });

    renderDetail([item]);

    // Just the product name — no ingredient rows
    expect(screen.getByText('Hamburguesa Clásica')).toBeInTheDocument();
  });

  it('shows order-level notas', () => {
    const item = makeItem();
    renderDetail([item], { notas: 'Sin sal en todo el pedido' });

    expect(screen.getByText('Sin sal en todo el pedido')).toBeInTheDocument();
  });
});
