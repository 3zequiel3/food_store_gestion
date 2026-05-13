import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ShoppingBag, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { AddressSelector } from './AddressSelector';
import { PaymentMethodSelector } from './PaymentMethodSelector';
import { OrderSummary } from './OrderSummary';
import { useCreateOrder } from '../hooks/useCreateOrder';
import { useCartStore } from '../../cart/stores/cartStore';
import { crearPedidoSchema } from '../schemas/checkoutSchema';
import type { CrearPedidoRequest, ItemPedidoPayload } from '../types/checkout.types';

/**
 * Página de checkout.
 *
 * Orquesta la selección de dirección, forma de pago y muestra el resumen.
 * Al confirmar, arma el payload, valida con Zod y envía la mutation.
 *
 * D1: No usa TanStack Form — cada selector maneja su estado local.
 * D4: El costo de envío se muestra como estimación (backend calcula el total real).
 */
export function CheckoutPage() {
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);
  const clearCart = useCartStore((s) => s.clearCart);

  // Estados locales de los selectores
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<string | null>(null);
  const [notas, setNotas] = useState('');

  const createOrderMutation = useCreateOrder();

  // Guard: si el carrito está vacío, mostrar mensaje (7.2)
  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="text-center space-y-4">
          <ShoppingBag className="h-16 w-16 text-muted-foreground/40 mx-auto" />
          <h1 className="text-2xl font-bold text-foreground">Tu carrito está vacío</h1>
          <p className="text-muted-foreground">
            Agregá productos del catálogo para continuar con tu pedido.
          </p>
          <button
            onClick={() => navigate('/cliente/catalogo')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Ir al catálogo
          </button>
        </div>
      </div>
    );
  }

  // Construir payload a partir del estado del carrito y selectores
  function buildOrderPayload(): CrearPedidoRequest {
    const itemsPayload: ItemPedidoPayload[] = items.map((item) => ({
      producto_id: item.producto_id,
      cantidad: item.cantidad,
      personalizacion: item.personalizacionIds ?? null,
    }));

    return {
      items: itemsPayload,
      forma_pago_codigo: selectedPaymentMethod!,
      direccion_id: selectedAddressId,
      notas: notas.trim() || null,
    };
  }

  function handleSubmit() {
    // Validar que se haya seleccionado forma de pago
    if (!selectedPaymentMethod) {
      toast.error('Seleccioná una forma de pago');
      return;
    }

    const payload = buildOrderPayload();

    // Validar con Zod antes de enviar
    const result = crearPedidoSchema.safeParse(payload);
    if (!result.success) {
      const errors = result.error.errors;
      if (errors.length > 0) {
        toast.error('Verificá los datos del pedido', {
          description: errors[0].message,
        });
      }
      return;
    }

    createOrderMutation.mutate(payload);
  }

  const isSubmitDisabled = !selectedPaymentMethod || createOrderMutation.isPending;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/cliente/catalogo')}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al catálogo
        </button>
        <h1 className="text-2xl font-bold text-foreground">Finalizar compra</h1>
        <p className="text-muted-foreground">
          Revisá los datos de tu pedido y seleccioná la forma de pago
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr,400px]">
        {/* Columna izquierda: selectores */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-4">
            <AddressSelector
              selectedAddressId={selectedAddressId}
              onSelect={setSelectedAddressId}
            />
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <PaymentMethodSelector
              selectedPaymentMethod={selectedPaymentMethod}
              onSelect={setSelectedPaymentMethod}
            />
          </div>
        </div>

        {/* Columna derecha: resumen y acción */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-4">
            <OrderSummary
              isLocalPickup={selectedAddressId === null}
              notas={notas}
              onNotasChange={setNotas}
            />
          </div>

          {/* Botón confirmar */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitDisabled}
            className="w-full h-12 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {createOrderMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Procesando...
              </>
            ) : (
              'Confirmar pedido'
            )}
          </button>

          {!selectedPaymentMethod && (
            <p className="text-xs text-center text-muted-foreground">
              Seleccioná una forma de pago para continuar
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
