/**
 * Tests — KitchenOrderCard component.
 *
 * Verifica:
 * - CONFIRMADO order → muestra botón "Iniciar preparación"
 * - EN_PREPARACION order → muestra botón "Terminado"
 * - Click en "Iniciar preparación" → llama onTransition con (orderId, 'EN_PREPARACION')
 * - Urgency badge se renderiza con colores según el tiempo
 * - Items se muestran con nombre y cantidad
 * - Exclusiones de personalización se muestran
 * - Notas del pedido se muestran
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CocinaPedidoResponse } from '../types/cocina.types';
import { KitchenOrderCard } from '../components/KitchenOrderCard';
import * as urgencyTimer from '../hooks/useUrgencyTimer';

// Mock useUrgencyTimer to control urgency output
vi.mock('../hooks/useUrgencyTimer', () => ({
  useUrgencyTimer: vi.fn(),
}));

const mockUseUrgencyTimer = vi.mocked(urgencyTimer.useUrgencyTimer);

function makeOrder(overrides: Partial<CocinaPedidoResponse> = {}): CocinaPedidoResponse {
  return {
    id: 1,
    estado: 'CONFIRMADO',
    items: [
      {
        producto_id: 10,
        nombre_snapshot: 'Hamburguesa Clásica',
        cantidad: 2,
        personalizacion: null,
        notas: null,
        ingredientes: [],
        exclusiones_nombres: [],
      },
    ],
    notas: null,
    cocina_entry_at: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderCard(
  order: CocinaPedidoResponse,
  onTransition: (orderId: number, targetState: string) => void = vi.fn(),
  isTransitioning = false,
) {
  return render(
    <KitchenOrderCard
      order={order}
      onTransition={onTransition}
      isTransitioning={isTransitioning}
    />,
  );
}

describe('KitchenOrderCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: normal urgency (5 min)
    mockUseUrgencyTimer.mockReturnValue({ elapsedMinutes: 5, level: 'normal' });
  });

  describe('CONFIRMADO order', () => {
    it('renders "Iniciar preparación" button', () => {
      renderCard(makeOrder({ estado: 'CONFIRMADO' }));
      expect(screen.getByRole('button', { name: /iniciar preparación/i })).toBeInTheDocument();
    });

    it('does NOT render "Terminado" button', () => {
      renderCard(makeOrder({ estado: 'CONFIRMADO' }));
      expect(screen.queryByRole('button', { name: /terminado/i })).not.toBeInTheDocument();
    });

    it('calls onTransition with (orderId, "EN_PREPARACION") when button is clicked', () => {
      const onTransition = vi.fn();
      renderCard(makeOrder({ id: 42, estado: 'CONFIRMADO' }), onTransition);

      fireEvent.click(screen.getByRole('button', { name: /iniciar preparación/i }));

      expect(onTransition).toHaveBeenCalledWith(42, 'EN_PREPARACION');
    });

    it('disables the button when isTransitioning is true', () => {
      renderCard(makeOrder({ estado: 'CONFIRMADO' }), vi.fn(), true);
      expect(screen.getByRole('button', { name: /iniciar preparación/i })).toBeDisabled();
    });
  });

  describe('EN_PREPARACION order', () => {
    it('renders "Terminado" button', () => {
      renderCard(makeOrder({ estado: 'EN_PREPARACION' }));
      expect(screen.getByRole('button', { name: /terminado/i })).toBeInTheDocument();
    });

    it('does NOT render "Iniciar preparación" button', () => {
      renderCard(makeOrder({ estado: 'EN_PREPARACION' }));
      expect(screen.queryByRole('button', { name: /iniciar preparación/i })).not.toBeInTheDocument();
    });

    it('calls onTransition with (orderId, "TERMINADO") when button is clicked', () => {
      const onTransition = vi.fn();
      renderCard(makeOrder({ id: 7, estado: 'EN_PREPARACION' }), onTransition);

      fireEvent.click(screen.getByRole('button', { name: /terminado/i }));

      expect(onTransition).toHaveBeenCalledWith(7, 'TERMINADO');
    });

    it('disables the button when isTransitioning is true', () => {
      renderCard(makeOrder({ estado: 'EN_PREPARACION' }), vi.fn(), true);
      expect(screen.getByRole('button', { name: /terminado/i })).toBeDisabled();
    });
  });

  describe('items display', () => {
    it('shows item names and quantities', () => {
      renderCard(makeOrder({
        items: [
          { producto_id: 1, nombre_snapshot: 'Pizza Margarita', cantidad: 1, personalizacion: null, notas: null, ingredientes: [], exclusiones_nombres: [] },
          { producto_id: 2, nombre_snapshot: 'Papas Fritas', cantidad: 3, personalizacion: null, notas: null, ingredientes: [], exclusiones_nombres: [] },
        ],
      }));

      expect(screen.getByText('Pizza Margarita')).toBeInTheDocument();
      expect(screen.getByText('× 1')).toBeInTheDocument();
      expect(screen.getByText('Papas Fritas')).toBeInTheDocument();
      expect(screen.getByText('× 3')).toBeInTheDocument();
    });

    it('shows exclusion notes by name when exclusiones_nombres is present', () => {
      renderCard(makeOrder({
        items: [
          {
            producto_id: 1,
            nombre_snapshot: 'Hamburguesa',
            cantidad: 1,
            personalizacion: [3, 7],
            notas: null,
            ingredientes: [
              { id: 3, nombre: 'Lechuga', es_removible: true },
              { id: 7, nombre: 'Tomate', es_removible: true },
            ],
            exclusiones_nombres: ['Lechuga', 'Tomate'],
          },
        ],
      }));

      // D10: names, not raw IDs
      expect(screen.getByText('(sin: Lechuga, Tomate)')).toBeInTheDocument();
    });

    it('falls back to IDs in exclusion text when exclusiones_nombres is empty but personalizacion has IDs', () => {
      renderCard(makeOrder({
        items: [
          {
            producto_id: 1,
            nombre_snapshot: 'Hamburguesa',
            cantidad: 1,
            personalizacion: [3, 7],
            notas: null,
            ingredientes: [],
            exclusiones_nombres: [],
          },
        ],
      }));

      // Fallback: show IDs when names unavailable (legacy data)
      expect(screen.getByText('(sin: 3, 7)')).toBeInTheDocument();
    });

    it('does NOT show exclusion text when personalizacion is null', () => {
      renderCard(makeOrder({
        items: [
          {
            producto_id: 1,
            nombre_snapshot: 'Ensalada',
            cantidad: 1,
            personalizacion: null,
            notas: null,
            ingredientes: [],
            exclusiones_nombres: [],
          },
        ],
      }));

      expect(screen.queryByText(/sin:/i)).not.toBeInTheDocument();
    });

    it('does NOT show exclusion text when personalizacion is empty array', () => {
      renderCard(makeOrder({
        items: [
          {
            producto_id: 1,
            nombre_snapshot: 'Ensalada',
            cantidad: 1,
            personalizacion: [],
            notas: null,
            ingredientes: [],
            exclusiones_nombres: [],
          },
        ],
      }));

      expect(screen.queryByText(/sin:/i)).not.toBeInTheDocument();
    });
  });

  describe('order notes', () => {
    it('shows order-level notes when present', () => {
      renderCard(makeOrder({ notas: 'Sin cebolla en todo el pedido' }));
      expect(screen.getByText('Sin cebolla en todo el pedido')).toBeInTheDocument();
    });

    it('does NOT show notes section when notas is null', () => {
      renderCard(makeOrder({ notas: null }));
      // The notes paragraph should not be rendered
      const notesElements = screen.queryAllByText(/sin cebolla/i);
      expect(notesElements).toHaveLength(0);
    });
  });

  describe('urgency badge', () => {
    it('renders with green (normal) level', () => {
      mockUseUrgencyTimer.mockReturnValue({ elapsedMinutes: 5, level: 'normal' });
      renderCard(makeOrder());

      expect(screen.getByText('5 min')).toBeInTheDocument();
      // Normal uses text-muted-foreground
      const badge = screen.getByText('5 min');
      expect(badge.className).toContain('text-muted-foreground');
    });

    it('renders with orange (warning) level', () => {
      mockUseUrgencyTimer.mockReturnValue({ elapsedMinutes: 15, level: 'warning' });
      renderCard(makeOrder());

      expect(screen.getByText('15 min')).toBeInTheDocument();
      const badge = screen.getByText('15 min');
      expect(badge.className).toContain('text-warning');
    });

    it('renders with red (critical) level and pulse animation', () => {
      mockUseUrgencyTimer.mockReturnValue({ elapsedMinutes: 25, level: 'critical' });
      renderCard(makeOrder());

      expect(screen.getByText('25 min')).toBeInTheDocument();
      const badge = screen.getByText('25 min');
      expect(badge.className).toContain('text-destructive');
      expect(badge.className).toContain('animate-pulse');
    });
  });

  describe('order number', () => {
    it('displays the order ID prominently', () => {
      renderCard(makeOrder({ id: 99 }));
      expect(screen.getByText('Pedido #99')).toBeInTheDocument();
    });
  });
});
