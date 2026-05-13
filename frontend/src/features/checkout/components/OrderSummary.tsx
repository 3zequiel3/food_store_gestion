import { useState } from 'react';
import { useCartStore } from '../../cart/stores/cartStore';

interface OrderSummaryProps {
  isLocalPickup: boolean;
  notas: string;
  onNotasChange: (notas: string) => void;
}

const SHIPPING_COST = 50; // Costo de envío fijo v1 (D5)

/**
 * Resumen del pedido.
 *
 * Muestra:
 * - Tabla de items (nombre, cantidad, precio unitario, subtotal)
 * - Costo de envío ($50 para domicilio, $0 para retiro en local)
 * - Total estimado
 * - Textarea para notas opcionales (max 500 chars)
 */
export function OrderSummary({ isLocalPickup, notas, onNotasChange }: OrderSummaryProps) {
  const items = useCartStore((s) => s.items);

  const subtotal = items.reduce((sum, item) => sum + Number(item.precio) * item.cantidad, 0);
  const shippingCost = isLocalPickup ? 0 : SHIPPING_COST;
  const estimatedTotal = subtotal + shippingCost;

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-foreground">Resumen del pedido</h3>

      {/* Tabla de items */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Producto</th>
              <th className="px-3 py-2 text-center font-medium text-muted-foreground">Cant.</th>
              <th className="px-3 py-2 text-right font-medium text-muted-foreground">Subtotal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item) => (
              <tr key={item.producto_id}>
                <td className="px-3 py-2">
                  <p className="font-medium text-foreground truncate max-w-[200px]">
                    {item.nombre}
                  </p>
                  {item.personalizacion && (
                    <p className="text-xs text-muted-foreground italic">
                      {item.personalizacion}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    ${Number(item.precio).toFixed(2)} c/u
                  </p>
                </td>
                <td className="px-3 py-2 text-center text-foreground">
                  {item.cantidad}
                </td>
                <td className="px-3 py-2 text-right font-medium text-foreground">
                  ${(Number(item.precio) * item.cantidad).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Totales */}
      <div className="space-y-2 bg-muted/30 p-3 rounded-lg">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Subtotal</span>
          <span className="text-foreground">${subtotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">
            Envío {isLocalPickup && '(Retiro en local)'}
          </span>
          <span className="text-foreground">${shippingCost.toFixed(2)}</span>
        </div>
        <div className="flex justify-between pt-2 border-t border-border">
          <span className="font-medium text-foreground">Total estimado</span>
          <span className="font-bold text-lg text-foreground">${estimatedTotal.toFixed(2)}</span>
        </div>
        <p className="text-xs text-muted-foreground">
          El total final se confirmará al procesar el pedido.
        </p>
      </div>

      {/* Notas */}
      <div className="space-y-2">
        <label htmlFor="notas" className="text-sm font-medium text-foreground">
          Notas (opcional)
        </label>
        <textarea
          id="notas"
          value={notas}
          onChange={(e) => onNotasChange(e.target.value)}
          placeholder="Instrucciones especiales para la entrega, alergias, etc."
          maxLength={500}
          rows={3}
          className="w-full px-3 py-2 text-sm bg-card border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Máximo 500 caracteres</span>
          <span>{notas.length}/500</span>
        </div>
      </div>
    </div>
  );
}
