/**
 * Tasks 5.1, 5.2 — AdminFaltantesPage resolver UI tests.
 *
 * 5.1: Exactly ONE "Resolver" button + ONE <select> with options
 *      "solucionado" and "comprado" per shortage row. No second primary CTA.
 *
 * 5.2: Clicking "Resolver" with selector set to "comprado" triggers the mutation
 *      with body { accion: "comprado" }. Default (unmodified selector) sends
 *      { accion: "solucionado" }.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Module mocks — must be declared before imports
// ---------------------------------------------------------------------------

const mockResolver = vi.fn();

vi.mock('../../../features/availability/hooks/useFaltantes', () => ({
  useFaltantes: vi.fn(() => ({
    data: [
      {
        id: 1,
        ingrediente_id: 10,
        ingrediente_nombre: 'Tomate',
        reportado_por: 3,
        pedido_id: 42,
        creado_en: '2026-05-28T10:00:00Z',
        resuelto_en: null,
        resuelto_por: null,
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useResolverFaltante: vi.fn(() => ({
    mutate: mockResolver,
    isPending: false,
  })),
  FALTANTES_QUERY_KEY: ['availability', 'faltantes'],
}));

vi.mock('../../../features/availability/stores/faltantesStore', () => ({
  useFaltantesStore: vi.fn((selector: (s: { reset: () => void }) => unknown) =>
    selector({ reset: vi.fn() }),
  ),
}));

// useAuthStore — canResolve = true (ADMIN)
vi.mock('../../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: {
    user: { id: number };
    hasRole: (r: string) => boolean;
  }) => unknown) =>
    selector({
      user: { id: 1 },
      hasRole: (role: string) => role === 'ADMIN',
    }),
  ),
}));

// useOrderWebSocket — no-op mock
vi.mock('../../../features/orders/hooks/useOrderWebSocket', () => ({
  useOrderWebSocket: vi.fn(() => ({ isConnected: false, isDegraded: true })),
}));

// Import AFTER mocks
import { AdminFaltantesPage } from '../AdminFaltantesPage';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AdminFaltantesPage />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Task 5.1 — UI structure: one Resolver button + one <select> per row
// ---------------------------------------------------------------------------

describe('AdminFaltantesPage — resolver UI structure (Task 5.1)', () => {
  beforeEach(() => {
    mockResolver.mockClear();
  });

  it('renders exactly ONE "Resolver" button per shortage row', () => {
    renderPage();

    const resolverButtons = screen.getAllByRole('button', { name: /resolver/i });
    // There must be exactly one button per row (we mocked 1 shortage row)
    expect(resolverButtons).toHaveLength(1);
  });

  it('renders exactly ONE <select> with solucionado and comprado options per row', () => {
    renderPage();

    const selects = screen.getAllByRole('combobox');
    expect(selects).toHaveLength(1);

    const select = selects[0];
    const options = within(select).getAllByRole('option');
    const optionValues = options.map((o) => o.getAttribute('value') ?? (o as HTMLOptionElement).value);

    expect(optionValues).toContain('solucionado');
    expect(optionValues).toContain('comprado');
  });

  it('does NOT render a second primary CTA (old "Ingrediente comprado" or "Solucionado" buttons)', () => {
    renderPage();

    // Old buttons were labeled "Ingrediente comprado" and "Solucionado"
    expect(screen.queryByRole('button', { name: /ingrediente comprado/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^solucionado$/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Task 5.2 — Mutation payload: accion reflects selected value
// ---------------------------------------------------------------------------

describe('AdminFaltantesPage — resolver mutation payload (Task 5.2)', () => {
  beforeEach(() => {
    mockResolver.mockClear();
  });

  it('sends accion="solucionado" when Resolver is clicked with default selector value', async () => {
    const user = userEvent.setup();
    renderPage();

    const resolverButton = screen.getByRole('button', { name: /resolver/i });
    await user.click(resolverButton);

    expect(mockResolver).toHaveBeenCalledOnce();
    expect(mockResolver).toHaveBeenCalledWith(
      expect.objectContaining({ accion: 'solucionado' }),
    );
  });

  it('sends accion="comprado" when selector is changed to comprado before clicking Resolver', async () => {
    const user = userEvent.setup();
    renderPage();

    const select = screen.getByRole('combobox');
    await user.selectOptions(select, 'comprado');

    const resolverButton = screen.getByRole('button', { name: /resolver/i });
    await user.click(resolverButton);

    expect(mockResolver).toHaveBeenCalledOnce();
    expect(mockResolver).toHaveBeenCalledWith(
      expect.objectContaining({ accion: 'comprado' }),
    );
  });
});
