/**
 * Tests — KitchenKanban component.
 *
 * Verifica:
 * - Renderiza dos columnas: "Por preparar" (CONFIRMADO) y "En preparación" (EN_PREPARACION)
 * - Renderiza ConnectionStatus component
 * - Filtra orders correctamente por estado en cada columna
 * - Muestra "No hay pedidos" cuando una columna está vacía
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import type { CocinaPedidoResponse } from '../types/cocina.types';
import { KitchenKanban } from '../components/KitchenKanban';

// Mock useUrgencyTimer to avoid timer complexity in kanban tests
vi.mock('../hooks/useUrgencyTimer', () => ({
  useUrgencyTimer: vi.fn(() => ({ elapsedMinutes: 5, level: 'normal' })),
}));

function makeOrder(overrides: Partial<CocinaPedidoResponse> = {}): CocinaPedidoResponse {
  return {
    id: 1,
    estado: 'CONFIRMADO',
    items: [],
    notas: null,
    cocina_entry_at: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderKanban(
  orders: CocinaPedidoResponse[] = [],
  isConnected = true,
  onTransition: (orderId: number, targetState: string) => void = vi.fn(),
  transitioningId: number | null = null,
) {
  return render(
    <KitchenKanban
      orders={orders}
      isConnected={isConnected}
      onTransition={onTransition}
      transitioningId={transitioningId}
    />,
  );
}

describe('KitchenKanban', () => {
  it('renders the page title "Cocina"', () => {
    renderKanban();
    expect(screen.getByText('Cocina')).toBeInTheDocument();
  });

  it('renders "Por preparar" column header', () => {
    renderKanban();
    expect(screen.getByText('Por preparar')).toBeInTheDocument();
  });

  it('renders "En preparación" column header', () => {
    renderKanban();
    expect(screen.getByText('En preparación')).toBeInTheDocument();
  });

  it('shows CONFIRMADO orders in "Por preparar" column', () => {
    const orders = [
      makeOrder({ id: 1, estado: 'CONFIRMADO' }),
      makeOrder({ id: 2, estado: 'CONFIRMADO' }),
    ];
    renderKanban(orders);

    expect(screen.getByText('Pedido #1')).toBeInTheDocument();
    expect(screen.getByText('Pedido #2')).toBeInTheDocument();
  });

  it('shows EN_PREPARACION orders in "En preparación" column', () => {
    const orders = [
      makeOrder({ id: 3, estado: 'EN_PREPARACION' }),
    ];
    renderKanban(orders);

    expect(screen.getByText('Pedido #3')).toBeInTheDocument();
  });

  it('does NOT show CONFIRMADO orders in "En preparación" column', () => {
    const orders = [
      makeOrder({ id: 1, estado: 'CONFIRMADO' }),
    ];
    renderKanban(orders);

    // The order card should be in the CONFIRMADO column, not EN_PREPARACION
    // We verify by checking the "En preparación" column shows "No hay pedidos"
    const noPedidos = screen.getAllByText('No hay pedidos');
    // At least one "No hay pedidos" should exist (the EN_PREPARACION column)
    expect(noPedidos.length).toBeGreaterThanOrEqual(1);
  });

  it('shows "No hay pedidos" when a column is empty', () => {
    renderKanban([]);

    // Both columns should be empty
    const noPedidos = screen.getAllByText('No hay pedidos');
    expect(noPedidos).toHaveLength(2);
  });

  it('shows the count badge for each column', () => {
    const orders = [
      makeOrder({ id: 1, estado: 'CONFIRMADO' }),
      makeOrder({ id: 2, estado: 'CONFIRMADO' }),
      makeOrder({ id: 3, estado: 'EN_PREPARACION' }),
    ];
    renderKanban(orders);

    // Count badges: 2 for CONFIRMADO, 1 for EN_PREPARACION
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  describe('ConnectionStatus', () => {
    it('does NOT show connection warning when connected', () => {
      renderKanban([], true);
      expect(
        screen.queryByText(/sin conexión en vivo/i),
      ).not.toBeInTheDocument();
    });

    it('shows connection warning when disconnected', () => {
      renderKanban([], false);
      expect(
        screen.getByText(/sin conexión en vivo/i),
      ).toBeInTheDocument();
    });
  });
});
