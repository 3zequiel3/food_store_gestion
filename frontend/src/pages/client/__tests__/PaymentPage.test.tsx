import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock useOrderDetail so we don't need a full React Query setup
vi.mock('../../../features/orders/hooks/useOrderDetail', () => ({
  useOrderDetail: vi.fn(() => ({
    data: { id: 42, total: '1500.00', estado_codigo: 'PENDIENTE' },
    isLoading: false,
  })),
}));

// Mock PaymentForm so we control when onPending fires
vi.mock('../../../features/payments/components/PaymentForm', () => ({
  PaymentForm: ({
    onPending,
    onSuccess,
    onError,
  }: {
    onPending: (response: object, message: string) => void;
    onSuccess: (response: object) => void;
    onError: (message: string) => void;
  }) => (
    <div data-testid="mock-payment-form">
      <button
        data-testid="trigger-pending"
        onClick={() =>
          onPending(
            { mp_status: 'pending', mp_id: 'mp_p', status_detail: 'pending_review_manual', pago_id: 5 },
            'Tu pago está en revisión. Te avisaremos cuando se confirme.',
          )
        }
      >
        Trigger Pending
      </button>
      <button
        data-testid="trigger-success"
        onClick={() =>
          onSuccess({ mp_status: 'approved', mp_id: 'mp_a', status_detail: 'accredited', pago_id: 6 })
        }
      >
        Trigger Success
      </button>
      <button data-testid="trigger-error" onClick={() => onError('Error genérico')}>
        Trigger Error
      </button>
    </div>
  ),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderPaymentPage(pedidoId = '42') {
  return render(
    <MemoryRouter initialEntries={[`/cliente/pedidos/${pedidoId}/pago`]}>
      <Routes>
        <Route
          path="/cliente/pedidos/:id/pago"
          element={<PaymentPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// Import after mocks
import { PaymentPage } from '../PaymentPage';

describe('PaymentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Task 10.1 — cuando PaymentForm dispara onPending, muestra el panel con el mensaje y botón
  it('muestra panel de pending con mensaje cuando PaymentForm dispara onPending', async () => {
    renderPaymentPage();

    fireEvent.click(screen.getByTestId('trigger-pending'));

    await waitFor(() => {
      expect(
        screen.getByText('Tu pago está en revisión. Te avisaremos cuando se confirme.'),
      ).toBeInTheDocument();
    });

    expect(screen.getByText('Ver estado del pedido')).toBeInTheDocument();
  });

  // Task 10.2 — al clickear "Ver estado del pedido" navega a /cliente/pedidos/{id}/confirmacion
  it('navega a /confirmacion al clickear "Ver estado del pedido"', async () => {
    renderPaymentPage();

    fireEvent.click(screen.getByTestId('trigger-pending'));

    await waitFor(() => {
      expect(screen.getByText('Ver estado del pedido')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Ver estado del pedido'));

    expect(mockNavigate).toHaveBeenCalledWith('/cliente/pedidos/42/confirmacion');
  });

  it('NO navega automáticamente cuando se muestra el panel pending', async () => {
    renderPaymentPage();

    fireEvent.click(screen.getByTestId('trigger-pending'));

    await waitFor(() => {
      expect(screen.getByText('Ver estado del pedido')).toBeInTheDocument();
    });

    // navigate must not have been called yet (only on explicit button click)
    expect(mockNavigate).not.toHaveBeenCalledWith(
      expect.stringContaining('confirmacion'),
    );
  });
});
