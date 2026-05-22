/**
 * Task 3.7 — P1.6: pre-checkout removable-ingredients review step.
 *
 * - Lists removable ingredients per cart item as toggles.
 * - Lists non-removable ingredients as fixed (not interactive).
 * - Toggling a removable ingredient records it in exclusions (personalizacionIds).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RemovableIngredientsStep } from '../RemovableIngredientsStep';

// ---------------------------------------------------------------------------
// Mock getProduct so we control what ingredients the step sees.
// ---------------------------------------------------------------------------

vi.mock('../../../products/services/products.service', () => ({
  getProduct: vi.fn(),
}));

import { getProduct } from '../../../products/services/products.service';

const mockGetProduct = getProduct as ReturnType<typeof vi.fn>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BURGER_PRODUCT = {
  id: 1,
  nombre: 'Hamburguesa clásica',
  descripcion: null,
  precio: 800,
  imagen_url: null,
  disponible: true,
  stock_cantidad: 10,
  categoria_id: null,
  imagenes: [],
  categorias: [],
  ingredientes: [
    { id: 10, nombre: 'Carne', es_alergeno: false, es_removible: false },
    { id: 11, nombre: 'Queso', es_alergeno: true, es_removible: true },
    { id: 12, nombre: 'Lechuga', es_alergeno: false, es_removible: true },
    { id: 13, nombre: 'Pan', es_alergeno: true, es_removible: false },
  ],
};

const PIZZA_PRODUCT = {
  id: 2,
  nombre: 'Pizza Margherita',
  descripcion: null,
  precio: 1200,
  imagen_url: null,
  disponible: true,
  stock_cantidad: 5,
  categoria_id: null,
  imagenes: [],
  categorias: [],
  ingredientes: [
    { id: 20, nombre: 'Mozzarella', es_alergeno: true, es_removible: true },
    { id: 21, nombre: 'Tomate', es_alergeno: false, es_removible: false },
  ],
};

function makeCartItems() {
  return [
    { producto_id: 1, nombre: 'Hamburguesa clásica', precio: 800, cantidad: 1 },
    { producto_id: 2, nombre: 'Pizza Margherita', precio: 1200, cantidad: 2 },
  ];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderStep(
  cartItems = makeCartItems(),
  exclusions: Record<number, Set<number>> = {},
  onExclusionsChange = vi.fn(),
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <RemovableIngredientsStep
        cartItems={cartItems}
        exclusions={exclusions}
        onExclusionsChange={onExclusionsChange}
      />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockGetProduct.mockImplementation((id: number) => {
    if (id === 1) return Promise.resolve(BURGER_PRODUCT);
    if (id === 2) return Promise.resolve(PIZZA_PRODUCT);
    return Promise.reject(new Error('Not found'));
  });
});

describe('RemovableIngredientsStep — renders ingredients', () => {
  it('shows each cart item header', async () => {
    renderStep();
    await waitFor(() => {
      expect(screen.getByText('Hamburguesa clásica')).toBeInTheDocument();
      expect(screen.getByText('Pizza Margherita')).toBeInTheDocument();
    });
  });

  it('renders removable ingredients as checkboxes (toggles)', async () => {
    renderStep();
    await waitFor(() => {
      // Burger: Queso and Lechuga are removible
      const quesoCb = screen.getByRole('checkbox', { name: /queso/i });
      const lechugaCb = screen.getByRole('checkbox', { name: /lechuga/i });
      expect(quesoCb).toBeInTheDocument();
      expect(lechugaCb).toBeInTheDocument();

      // Pizza: Mozzarella is removible
      const mozzaCb = screen.getByRole('checkbox', { name: /mozzarella/i });
      expect(mozzaCb).toBeInTheDocument();
    });
  });

  it('renders non-removable ingredients as fixed (no checkbox)', async () => {
    renderStep();
    await waitFor(() => {
      // Carne and Pan are NOT removable — no checkbox, but text should still appear
      expect(screen.queryByRole('checkbox', { name: /carne/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('checkbox', { name: /pan/i })).not.toBeInTheDocument();
      // They appear as text
      expect(screen.getByText('Carne')).toBeInTheDocument();
      expect(screen.getByText('Pan')).toBeInTheDocument();
    });
  });

  it('all removable checkboxes are checked by default (included)', async () => {
    renderStep();
    await waitFor(() => {
      const quesoCb = screen.getByRole('checkbox', { name: /queso/i });
      expect(quesoCb).toBeChecked();
    });
  });
});

describe('RemovableIngredientsStep — toggling records exclusions', () => {
  it('unchecking a removable ingredient calls onExclusionsChange with that ingredient excluded', async () => {
    const onExclusionsChange = vi.fn();
    renderStep(makeCartItems(), {}, onExclusionsChange);

    await waitFor(() => {
      expect(screen.getByRole('checkbox', { name: /queso/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('checkbox', { name: /queso/i }));

    expect(onExclusionsChange).toHaveBeenCalledOnce();
    // producto_id 1, ingredient id 11 should be excluded
    const [pid, newSet] = onExclusionsChange.mock.calls[0];
    expect(pid).toBe(1);
    expect(newSet).toBeInstanceOf(Set);
    expect(newSet.has(11)).toBe(true);
  });

  it('re-checking a previously excluded ingredient removes it from exclusions', async () => {
    // Start with queso (id 11) already excluded for product 1
    const initialExclusions: Record<number, Set<number>> = { 1: new Set([11]) };
    const onExclusionsChange = vi.fn();
    renderStep(makeCartItems(), initialExclusions, onExclusionsChange);

    await waitFor(() => {
      const quesoCb = screen.getByRole('checkbox', { name: /queso/i });
      // Should appear unchecked because it's excluded
      expect(quesoCb).not.toBeChecked();
    });

    fireEvent.click(screen.getByRole('checkbox', { name: /queso/i }));

    expect(onExclusionsChange).toHaveBeenCalledOnce();
    const [pid, newSet] = onExclusionsChange.mock.calls[0];
    expect(pid).toBe(1);
    expect(newSet.has(11)).toBe(false);
  });
});

describe('RemovableIngredientsStep — no removable ingredients', () => {
  it('shows a message when a product has no removable ingredients', async () => {
    mockGetProduct.mockResolvedValue({
      ...BURGER_PRODUCT,
      ingredientes: [
        { id: 10, nombre: 'Carne', es_alergeno: false, es_removible: false },
      ],
    });
    renderStep([{ producto_id: 1, nombre: 'Hamburguesa', precio: 800, cantidad: 1 }]);

    await waitFor(() => {
      expect(screen.getByText(/no hay ingredientes removibles/i)).toBeInTheDocument();
    });
  });
});
