import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OrderStatusBadge } from '../OrderStatusBadge';
import type { EstadoCodigo } from '../../types/orders.types';

describe('OrderStatusBadge', () => {
  it('renders label and variant for each standard state', () => {
    const cases: { estado: EstadoCodigo; label: string; variantClass: string }[] = [
      { estado: 'PENDIENTE', label: 'Pendiente', variantClass: 'bg-warning/15' },
      { estado: 'CONFIRMADO', label: 'Confirmado', variantClass: 'bg-info/15' },
      { estado: 'EN_PREPARACION', label: 'En preparación', variantClass: 'bg-primary/15' },
      { estado: 'TERMINADO', label: 'Listo para retirar/entregar', variantClass: 'bg-info/15' },
      { estado: 'ENTREGADO', label: 'Entregado', variantClass: 'bg-success/15' },
    ];

    cases.forEach(({ estado, label, variantClass }) => {
      const { unmount } = render(<OrderStatusBadge estado={estado} />);
      const badge = screen.getByText(label);
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain(variantClass);
      unmount();
    });
  });

  it('renders destructive variant for CANCELADO', () => {
    render(<OrderStatusBadge estado="CANCELADO" />);
    const badge = screen.getByText('Cancelado');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-destructive/15');
  });

  it('renders destructive variant and explicit label for CANCELADO_ADMIN', () => {
    render(<OrderStatusBadge estado="CANCELADO_ADMIN" />);
    const badge = screen.getByText('Cancelado (Admin)');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-destructive/15');
  });

  it('renders destructive variant and explicit label for CANCELADO_CLIENTE', () => {
    render(<OrderStatusBadge estado="CANCELADO_CLIENTE" />);
    const badge = screen.getByText('Cancelado (Cliente)');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('bg-destructive/15');
  });
});
