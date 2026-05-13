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
import { Button } from '../../../components/ui/Button';

export function CheckoutPage() {
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);
  const clearCart = useCartStore((s) => s.clearCart);

  // Estados locales de los selectores
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<string | null>(null);
  const [notas, setNotas] = useState('');

  const createOrderMutation = useCreateOrder();

  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="h-16 w-16 rounded-2xl bg-glass backdrop-blur-xl border border-glass-border flex items-center justify-center">
              <ShoppingBag className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground">Tu carrito está vacío</h1>
          <p className="text-muted-foreground">
            Agregá productos del catálogo para continuar con tu pedido.
          </p>
          <Button onClick={() => navigate('/cliente/catalogo')} leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Ir al catálogo
          </Button>
        </div>
      </div>
    );
  }

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
    if (!selectedPaymentMethod) {
      toast.error('Seleccioná una forma de pago');
      return;
    }

    const payload = buildOrderPayload();

    const result = crearPedidoSchema.safeParse(payload);
    if (!result.success) {
      const errors = result.error.issues;
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
      <div className="mb-8">
        <button
          onClick={() => navigate('/cliente/catalogo')}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al catálogo
        </button>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          Finalizar compra
        </h1>
        <p className="text-muted-foreground mt-1">
          Revisá los datos de tu pedido y seleccioná la forma de pago
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr,400px]">
        <div className="space-y-6">
          <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-5 shadow-sm">
            <AddressSelector
              selectedAddressId={selectedAddressId}
              onSelect={setSelectedAddressId}
            />
          </div>

          <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-5 shadow-sm">
            <PaymentMethodSelector
              selectedPaymentMethod={selectedPaymentMethod}
              onSelect={setSelectedPaymentMethod}
            />
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-5 shadow-sm">
            <OrderSummary
              isLocalPickup={selectedAddressId === null}
              notas={notas}
              onNotasChange={setNotas}
            />
          </div>

          <Button
            onClick={handleSubmit}
            disabled={isSubmitDisabled}
            size="lg"
            isLoading={createOrderMutation.isPending}
            className="w-full"
          >
            {createOrderMutation.isPending ? 'Procesando...' : 'Confirmar pedido'}
          </Button>

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
