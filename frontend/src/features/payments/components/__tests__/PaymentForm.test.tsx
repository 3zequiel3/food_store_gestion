import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PaymentForm } from '../PaymentForm';
import * as paymentsService from '../../services/payments.service';
import type { PaymentResponse } from '../../types/payments.types';

type OnSuccessHandler = (response: PaymentResponse) => void;
type OnPendingHandler = (response: PaymentResponse, message: string) => void;
type OnErrorHandler = (message: string) => void;

vi.mock('../../services/payments.service', () => ({
  createInlinePayment: vi.fn(),
}));

vi.mock('../SecureCardForm', () => ({
  SecureCardForm: ({
    onSubmit,
    onError,
    isLoading,
  }: {
    onSubmit: (token: string, pmId: string, idType: string, idNumber: string) => void;
    onError: (msg: string) => void;
    isLoading?: boolean;
  }) => (
    <div data-testid="mock-secure-card-form">
      <button
        data-testid="mock-submit"
        onClick={() => onSubmit('tok_test', 'visa', 'DNI', '12345678')}
        disabled={isLoading}
      >
        Pay
      </button>
      <button data-testid="mock-error" onClick={() => onError('Card declined')}>
        Simulate Error
      </button>
    </div>
  ),
}));

const mockCreateInlinePayment = vi.mocked(paymentsService.createInlinePayment);

// Helper: renderiza PaymentForm con todos los callbacks
function renderPaymentForm(overrides?: {
  onSuccess?: ReturnType<typeof vi.fn<OnSuccessHandler>>;
  onPending?: ReturnType<typeof vi.fn<OnPendingHandler>>;
  onError?: ReturnType<typeof vi.fn<OnErrorHandler>>;
}) {
  const onSuccess = overrides?.onSuccess ?? vi.fn<OnSuccessHandler>();
  const onPending = overrides?.onPending ?? vi.fn<OnPendingHandler>();
  const onError = overrides?.onError ?? vi.fn<OnErrorHandler>();
  render(
    <PaymentForm
      pedidoId={1}
      onSuccess={onSuccess}
      onPending={onPending}
      onError={onError}
    />,
  );
  return { onSuccess, onPending, onError };
}

describe('PaymentForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls createInlinePayment with correct payload on submit', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'approved',
      mp_id: 'mp_1',
      status_detail: 'accredited',
      pago_id: 7,
    });

    const { onSuccess } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(mockCreateInlinePayment).toHaveBeenCalledWith(
        expect.objectContaining({
          pedido_id: 1,
          card_token: 'tok_test',
          payment_method_id: 'visa',
          installments: 1,
          identification_type: 'DNI',
          identification_number: '12345678',
        }),
      );
    });
    expect(mockCreateInlinePayment).toHaveBeenCalledWith(
      expect.objectContaining({
        idempotency_key: expect.stringMatching(
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
        ),
      }),
    );
    expect(onSuccess).toHaveBeenCalled();
  });

  // Task 8.3 — dispara onSuccess cuando mp_status es approved
  it('dispara onSuccess cuando mp_status es approved', async () => {
    const response = {
      mp_status: 'approved',
      mp_id: 'mp_1',
      status_detail: 'accredited',
      pago_id: 7,
    };
    mockCreateInlinePayment.mockResolvedValueOnce(response);

    const { onSuccess, onPending, onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(response);
    });
    expect(onPending).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  // Task 8.4 — dispara onPending cuando mp_status es pending con mensaje user-friendly
  it('dispara onPending cuando mp_status es pending con mensaje user-friendly', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'pending',
      mp_id: 'mp_2',
      status_detail: 'pending_review_manual',
      pago_id: 8,
    });

    const { onSuccess, onPending, onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onPending).toHaveBeenCalledWith(
        expect.objectContaining({ mp_status: 'pending' }),
        'Tu pago está en revisión. Te avisaremos cuando se confirme.',
      );
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  // Task 8.5 — dispara onPending cuando mp_status es in_process
  it('dispara onPending cuando mp_status es in_process', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'in_process',
      mp_id: 'mp_3',
      status_detail: 'pending_waiting_payment',
      pago_id: 9,
    });

    const { onPending, onSuccess, onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onPending).toHaveBeenCalledWith(
        expect.objectContaining({ mp_status: 'in_process' }),
        'Tu pago está pendiente de procesamiento.',
      );
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  // Task 8.6 — dispara onPending cuando mp_status es authorized
  it('dispara onPending cuando mp_status es authorized', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'authorized',
      mp_id: 'mp_4',
      status_detail: null,
      pago_id: 10,
    });

    const { onPending, onSuccess, onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onPending).toHaveBeenCalled();
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  // Task 8.7 — dispara onError con status_detail mapeado cuando rejected
  it('dispara onError con status_detail mapeado cuando rejected y status_detail es cc_rejected_insufficient_amount', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'rejected',
      mp_id: null,
      status_detail: 'cc_rejected_insufficient_amount',
      pago_id: 11,
    });

    const { onError, onSuccess, onPending } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Saldo insuficiente. Probá con otra tarjeta.');
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onPending).not.toHaveBeenCalled();
  });

  // Task 8.8 — dispara onError con status_detail crudo cuando not mapped
  it('dispara onError con status_detail crudo cuando rejected y status_detail no está mapeado', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'rejected',
      mp_id: null,
      status_detail: 'cc_some_new_detail_unknown',
      pago_id: 12,
    });

    const { onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('cc_some_new_detail_unknown');
    });
  });

  // Task 8.9 — dispara onError cuando mp_status es cancelled
  it('dispara onError cuando mp_status es cancelled', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'cancelled',
      mp_id: null,
      status_detail: null,
      pago_id: 13,
    });

    const { onError, onSuccess, onPending } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Sin información adicional.');
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onPending).not.toHaveBeenCalled();
  });

  // Task 8.10 — dispara onError con "Resultado inesperado" cuando mp_status es refunded
  it('dispara onError con mensaje "Resultado inesperado" cuando mp_status es refunded', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'refunded',
      mp_id: null,
      status_detail: null,
      pago_id: 14,
    });

    const { onError } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Resultado inesperado: refunded');
    });
  });

  // Task 8.11 — cae al catch y dispara onError cuando createInlinePayment rechaza con ApiError
  it('cae al catch y dispara onError cuando createInlinePayment rechaza con ApiError', async () => {
    const error = new Error('502 mp_unreachable');
    mockCreateInlinePayment.mockRejectedValueOnce(error);

    const { onError, onSuccess, onPending } = renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('502 mp_unreachable');
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onPending).not.toHaveBeenCalled();
  });

  it('disables submit during processing', async () => {
    mockCreateInlinePayment.mockImplementation(() => new Promise(() => {}));

    renderPaymentForm();

    fireEvent.click(screen.getByTestId('mock-submit'));

    expect(screen.getByTestId('mock-submit')).toBeDisabled();
  });
});
