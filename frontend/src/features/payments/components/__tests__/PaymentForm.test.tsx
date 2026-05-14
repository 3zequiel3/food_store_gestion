import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PaymentForm } from '../PaymentForm';
import * as paymentsService from '../../services/payments.service';

vi.mock('../../services/payments.service', () => ({
  createInlinePayment: vi.fn(),
}));

vi.mock('../SecureCardForm', () => ({
  SecureCardForm: ({ onSubmit, onError, isLoading }: {
    onSubmit: (token: string, pmId: string) => void;
    onError: (msg: string) => void;
    isLoading?: boolean;
  }) => (
    <div data-testid="mock-secure-card-form">
      <button
        data-testid="mock-submit"
        onClick={() => onSubmit('tok_test', 'visa')}
        disabled={isLoading}
      >
        Pay
      </button>
      <button
        data-testid="mock-error"
        onClick={() => onError('Card declined')}
      >
        Simulate Error
      </button>
    </div>
  ),
}));

const mockCreateInlinePayment = vi.mocked(paymentsService.createInlinePayment);

describe('PaymentForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls createInlinePayment with correct payload on submit', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'approved',
      mp_id: 'mp_1',
      status_detail: 'accredited',
    });

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(mockCreateInlinePayment).toHaveBeenCalledWith(
        expect.objectContaining({
          pedido_id: 1,
          monto: 1500,
          card_token: 'tok_test',
          payment_method_id: 'visa',
          installments: 1,
        }),
      );
    });
    // idempotency_key should be a valid UUID
    expect(mockCreateInlinePayment).toHaveBeenCalledWith(
      expect.objectContaining({
        idempotency_key: expect.stringMatching(
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
        ),
      }),
    );
  });

  it('calls onSuccess when payment is approved', async () => {
    const response = { mp_status: 'approved', mp_id: 'mp_1', status_detail: 'accredited' };
    mockCreateInlinePayment.mockResolvedValueOnce(response);

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(response);
    });
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError when payment is rejected', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'rejected',
      mp_id: null,
      status_detail: 'cc_rejected_bad_filled_card_number',
    });

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('cc_rejected_bad_filled_card_number');
    });
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('calls onError with default message when rejected without detail', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'rejected',
      mp_id: null,
      status_detail: null,
    });

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Pago rechazado. Intentá con otra tarjeta.');
    });
  });

  it('calls onError when payment is cancelled', async () => {
    mockCreateInlinePayment.mockResolvedValueOnce({
      mp_status: 'cancelled',
      mp_id: null,
      status_detail: null,
    });

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Pago rechazado. Intentá con otra tarjeta.');
    });
  });

  it('disables submit during processing', async () => {
    mockCreateInlinePayment.mockImplementation(
      () => new Promise(() => {}),
    );

    const onSuccess = vi.fn();
    const onError = vi.fn();

    render(
      <PaymentForm
        pedidoId={1}
        monto={1500}
        onSuccess={onSuccess}
        onError={onError}
      />,
    );

    fireEvent.click(screen.getByTestId('mock-submit'));

    // The button should be disabled because isLoading=true
    expect(screen.getByTestId('mock-submit')).toBeDisabled();
  });
});
