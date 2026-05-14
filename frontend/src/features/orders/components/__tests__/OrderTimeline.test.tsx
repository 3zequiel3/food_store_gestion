import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OrderTimeline } from '../OrderTimeline';
import type { HistorialEstado } from '../../types/orders.types';

const baseHistorial: HistorialEstado[] = [
  {
    id: 1,
    estado_anterior_codigo: null,
    estado_nuevo_codigo: 'PENDIENTE',
    cambiado_por_id: null,
    motivo: null,
    creado_en: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    estado_anterior_codigo: 'PENDIENTE',
    estado_nuevo_codigo: 'CONFIRMADO',
    cambiado_por_id: 1,
    motivo: null,
    creado_en: '2025-01-01T00:01:00Z',
  },
];

describe('OrderTimeline', () => {
  it('renders empty state message', () => {
    render(<OrderTimeline historial={[]} />);
    expect(screen.getByText('Sin historial de estados.')).toBeInTheDocument();
  });

  it('shows state progression for completed and current states', () => {
    render(
      <OrderTimeline
        historial={baseHistorial}
        currentEstado="CONFIRMADO"
      />,
    );

    // State labels appear in both progress bar and history list
    const pendienteElements = screen.getAllByText('Pendiente');
    const confirmadoElements = screen.getAllByText('Confirmado');
    expect(pendienteElements.length).toBeGreaterThan(0);
    expect(confirmadoElements.length).toBeGreaterThan(0);
  });

  it('shows cancelled state in red', () => {
    const cancelHistorial: HistorialEstado[] = [
      ...baseHistorial,
      {
        id: 3,
        estado_anterior_codigo: 'CONFIRMADO',
        estado_nuevo_codigo: 'CANCELADO',
        cambiado_por_id: 1,
        motivo: 'Cliente cambió de opinión',
        creado_en: '2025-01-01T00:02:00Z',
      },
    ];

    render(
      <OrderTimeline
        historial={cancelHistorial}
        currentEstado="CANCELADO"
      />,
    );

    const cancelElements = screen.getAllByText('Cancelado');
    expect(cancelElements.length).toBeGreaterThan(0);
    // Check that at least one has the destructive color class
    const hasDestructive = cancelElements.some(
      (el) => el.className.includes('text-destructive'),
    );
    expect(hasDestructive).toBe(true);
  });

  it('displays motivo when present in history entry', () => {
    const historialWithMotivo: HistorialEstado[] = [
      {
        id: 1,
        estado_anterior_codigo: null,
        estado_nuevo_codigo: 'CANCELADO',
        cambiado_por_id: 1,
        motivo: 'Pedido duplicado',
        creado_en: '2025-01-01T00:00:00Z',
      },
    ];

    render(<OrderTimeline historial={historialWithMotivo} currentEstado="CANCELADO" />);
    expect(screen.getByText('Pedido duplicado')).toBeInTheDocument();
  });

  it('shows future states in the progress bar', () => {
    render(
      <OrderTimeline
        historial={baseHistorial}
        currentEstado="CONFIRMADO"
      />,
    );

    // Future states should be visible in the progress bar
    expect(screen.getByText('En preparación')).toBeInTheDocument();
    expect(screen.getByText('En camino')).toBeInTheDocument();
    expect(screen.getByText('Entregado')).toBeInTheDocument();
  });
});
