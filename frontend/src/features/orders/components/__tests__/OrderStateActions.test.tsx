import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OrderStateActions } from '../OrderStateActions';
import type { PedidoDetalle } from '../../types/orders.types';

// Mock the mutation hook
vi.mock('../../hooks/useTransitionOrderState', () => ({
  useTransitionOrderState: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  })),
}));

function makeOrder(estado_codigo: PedidoDetalle['estado_codigo']): PedidoDetalle {
  return {
    id: 1,
    user_id: 10,
    estado_codigo,
    total: '1500.00',
    costo_envio: '0.00',
    forma_pago_codigo: 'EFECTIVO',
    direccion_snapshot: null,
    notas: null,
    creado_en: '2026-01-01T00:00:00Z',
    actualizado_en: null,
    items: [],
    historial: [],
    pagos: [],
  };
}

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

// ---------------------------------------------------------------------------
// Task 2.5 — P3.11: PENDIENTE order must NOT show a "Confirmar pedido" button.
// ---------------------------------------------------------------------------

describe('OrderStateActions — PENDIENTE state (P3.11)', () => {
  it('does NOT render a CONFIRMADO / "Confirmar pedido" action for a PENDIENTE order', () => {
    renderWithClient(<OrderStateActions order={makeOrder('PENDIENTE')} />);

    // The confirmation action has been removed; only admin-initiated actions remain.
    expect(screen.queryByRole('button', { name: /confirmar pedido/i })).not.toBeInTheDocument();

    // No button whose accessible name contains "confirmado" (case-insensitive)
    const buttons = screen.queryAllByRole('button');
    const confirmadoBtn = buttons.find((b) =>
      /confirmado/i.test(b.textContent ?? ''),
    );
    expect(confirmadoBtn).toBeUndefined();
  });

  it('still renders the Rechazar (cancel) action for a PENDIENTE order', () => {
    renderWithClient(<OrderStateActions order={makeOrder('PENDIENTE')} />);
    expect(screen.getByRole('button', { name: /rechazar/i })).toBeInTheDocument();
  });

  it('renders no actions at all for PENDIENTE (CONFIRMADO is webhook-only)', () => {
    // After P3.11 the PENDIENTE → CONFIRMADO transition is gone.
    // The only remaining action was Rechazar (danger). That should still be there,
    // so the panel should not be empty — but no primary action should exist.
    renderWithClient(<OrderStateActions order={makeOrder('PENDIENTE')} />);

    // No primary-variant button (bg-primary class indicates primary variant)
    const buttons = screen.queryAllByRole('button');
    const primaryBtns = buttons.filter((b) => b.className.includes('bg-primary'));
    expect(primaryBtns).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Regression: other states still work correctly.
// ---------------------------------------------------------------------------

describe('OrderStateActions — CONFIRMADO state', () => {
  it('renders "Iniciar preparación" as primary action', () => {
    renderWithClient(<OrderStateActions order={makeOrder('CONFIRMADO')} />);
    expect(
      screen.getByRole('button', { name: /iniciar preparación/i }),
    ).toBeInTheDocument();
  });

  it('renders a cancel/Cancelar action for CONFIRMADO', () => {
    renderWithClient(<OrderStateActions order={makeOrder('CONFIRMADO')} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
  });
});

describe('OrderStateActions — EN_PREPARACION state', () => {
  it('renders "Marcar listo" action', () => {
    renderWithClient(<OrderStateActions order={makeOrder('EN_PREPARACION')} />);
    expect(screen.getByRole('button', { name: /marcar listo/i })).toBeInTheDocument();
  });
});

describe('OrderStateActions — terminal states', () => {
  it('renders nothing for CANCELADO_ADMIN', () => {
    const { container } = renderWithClient(
      <OrderStateActions order={makeOrder('CANCELADO_ADMIN')} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing for ENTREGADO', () => {
    const { container } = renderWithClient(
      <OrderStateActions order={makeOrder('ENTREGADO')} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
