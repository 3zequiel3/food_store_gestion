import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OrderConfirmationPage } from '../OrderConfirmationPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../hooks/useOrderDetail', () => ({
  useOrderDetail: vi.fn(),
}));

import { useOrderDetail } from '../../hooks/useOrderDetail';

const mockUseOrderDetail = vi.mocked(useOrderDetail);

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderWithRouter(
  ui: React.ReactElement,
  { route = '/cliente/pedidos/42/confirmacion', state = null as any } = {},
) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[{ pathname: route, state }]}>
        <Routes>
          <Route path="/cliente/pedidos/:id/confirmacion" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('OrderConfirmationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders fallback when no location state and no order detail', () => {
    mockUseOrderDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);

    renderWithRouter(<OrderConfirmationPage />);

    expect(screen.getByText('Pedido creado')).toBeInTheDocument();
    expect(screen.getByText(/pedido #42/)).toBeInTheDocument();
  });

  it('shows real total from order detail when available', () => {
    mockUseOrderDetail.mockReturnValue({
      data: {
        id: 42,
        total: '1250.00',
        estado_codigo: 'PENDIENTE',
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithRouter(<OrderConfirmationPage />, {
      state: {
        pedido: { pedido_id: 42, pago_id: 1, mp_status: 'approved', mp_id: 'x', status_detail: 'accredited' },
        paymentStatus: 'approved',
      },
    });

    expect(screen.getByText('$1.250,00')).toBeInTheDocument();
  });

  it('shows fallback total placeholder when detail is unavailable but online payment', () => {
    mockUseOrderDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);

    renderWithRouter(<OrderConfirmationPage />, {
      state: {
        pedido: { pedido_id: 42, pago_id: 1, mp_status: 'approved', mp_id: 'x', status_detail: 'accredited' },
        paymentStatus: 'approved',
      },
    });

    expect(screen.getByText('$Pagado')).toBeInTheDocument();
  });

  it('shows fallback total placeholder for pickup+efectivo when detail unavailable', () => {
    mockUseOrderDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);

    renderWithRouter(<OrderConfirmationPage />, {
      state: {
        pedido: { pedido_id: 42 },
        paymentMethod: 'efectivo',
      },
    });

    expect(screen.getByText('$Pendiente')).toBeInTheDocument();
  });

  it('fetches order detail by pedido_id from URL on refresh (no state)', () => {
    mockUseOrderDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);

    renderWithRouter(<OrderConfirmationPage />);

    expect(mockUseOrderDetail).toHaveBeenCalledWith(42);
  });
});
