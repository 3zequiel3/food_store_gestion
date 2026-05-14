import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PaymentMethodSelector } from '../PaymentMethodSelector';
import * as usePaymentMethodsHook from '../../hooks/usePaymentMethods';

vi.mock('../../hooks/usePaymentMethods', () => ({
  usePaymentMethods: vi.fn(),
}));

const mockUsePaymentMethods = vi.mocked(usePaymentMethodsHook.usePaymentMethods);

const paymentMethods = [
  { codigo: 'EFECTIVO', descripcion: 'Efectivo', habilitada: true },
  { codigo: 'MERCADOPAGO', descripcion: 'MercadoPago', habilitada: true },
];

describe('PaymentMethodSelector', () => {
  it('shows all payment methods when isDelivery is false', () => {
    mockUsePaymentMethods.mockReturnValue({
      data: paymentMethods,
      isLoading: false,
    } as any);

    render(
      <PaymentMethodSelector
        selectedPaymentMethod={null}
        onSelect={() => {}}
        isDelivery={false}
      />,
    );

    expect(screen.getByText('Efectivo')).toBeInTheDocument();
    expect(screen.getByText('MercadoPago')).toBeInTheDocument();
  });

  it('filters out EFECTIVO when isDelivery is true', () => {
    mockUsePaymentMethods.mockReturnValue({
      data: paymentMethods,
      isLoading: false,
    } as any);

    render(
      <PaymentMethodSelector
        selectedPaymentMethod={null}
        onSelect={() => {}}
        isDelivery={true}
      />,
    );

    expect(screen.queryByText('Efectivo')).not.toBeInTheDocument();
    expect(screen.getByText('MercadoPago')).toBeInTheDocument();
  });

  it('shows delivery info message when isDelivery is true', () => {
    mockUsePaymentMethods.mockReturnValue({
      data: paymentMethods,
      isLoading: false,
    } as any);

    render(
      <PaymentMethodSelector
        selectedPaymentMethod={null}
        onSelect={() => {}}
        isDelivery={true}
      />,
    );

    expect(
      screen.getByText('Para envíos, aceptamos tarjeta o transferencia bancaria.'),
    ).toBeInTheDocument();
  });

  it('does not show delivery info message when isDelivery is false', () => {
    mockUsePaymentMethods.mockReturnValue({
      data: paymentMethods,
      isLoading: false,
    } as any);

    render(
      <PaymentMethodSelector
        selectedPaymentMethod={null}
        onSelect={() => {}}
        isDelivery={false}
      />,
    );

    expect(
      screen.queryByText('Para envíos, aceptamos tarjeta o transferencia bancaria.'),
    ).not.toBeInTheDocument();
  });
});
