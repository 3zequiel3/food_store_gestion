import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingBag, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { AddressSelector } from './AddressSelector';
import { PaymentMethodSelector } from './PaymentMethodSelector';
import { OrderSummary } from './OrderSummary';
import { SecureCardForm } from '../../payments/components/SecureCardForm';
import { useCheckoutOnline } from '../hooks/useCheckoutOnline';
import { useCheckoutPickupEfectivo } from '../hooks/useCheckoutPickupEfectivo';
import { useCartStore } from '../../cart/stores/cartStore';
import type {
  CheckoutItem,
  CheckoutOnlineRequest,
  CheckoutPickupEfectivoRequest,
} from '../types/checkout.types';
import { Button } from '../../../components/ui/Button';

/**
 * CheckoutPage — integrated checkout with inline payment.
 *
 * Refactored for checkout-pay-first-flow change:
 * - Online payment: collects card data inline, calls POST /checkout/online
 * - Pickup+efectivo: calls POST /checkout/pickup-efectivo
 * - No separate PaymentPage — everything happens here
 */
export function CheckoutPage() {
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);

  // Local state for selectors
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<string | null>(null);
  const [notas, setNotas] = useState('');

  // Idempotency key — generated once per checkout session
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => crypto.randomUUID());

  // Card token state (for online payment)
  const [cardToken, setCardToken] = useState<string | null>(null);
  const [paymentMethodId, setPaymentMethodId] = useState<string | null>(null);
  const [identificationType, setIdentificationType] = useState<string>('DNI');
  const [identificationNumber, setIdentificationNumber] = useState<string>('');

  const checkoutOnlineMutation = useCheckoutOnline();
  const checkoutPickupMutation = useCheckoutPickupEfectivo();

  // Delivery mode: true when an address is selected (not local pickup)
  const isDelivery = selectedAddressId !== null;

  // Reset payment selection if user had EFECTIVO and switches to delivery
  useEffect(() => {
    if (isDelivery && selectedPaymentMethod === 'EFECTIVO') {
      setSelectedPaymentMethod(null);
      toast.info('Efectivo no disponible para envíos', {
        description: 'Seleccioná otra forma de pago.',
      });
    }
  }, [isDelivery, selectedPaymentMethod]);

  // Regenerate idempotency key if user navigates away and comes back
  useEffect(() => {
    return () => {
      // On unmount, clear the key so next checkout gets a fresh one
      setIdempotencyKey(crypto.randomUUID());
    };
  }, []);

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

  function buildCheckoutItems(): CheckoutItem[] {
    return items.map((item) => ({
      producto_id: item.producto_id,
      cantidad: item.cantidad,
      personalizacion: item.personalizacionIds ?? null,
    }));
  }

  function handleCheckoutOnline() {
    if (!cardToken || !paymentMethodId) {
      toast.error('Completá los datos de la tarjeta');
      return;
    }

    const payload: CheckoutOnlineRequest = {
      items: buildCheckoutItems(),
      tipo_entrega: isDelivery ? 'DELIVERY' : 'PICKUP',
      direccion_id: selectedAddressId,
      notas: notas.trim() || null,
      card_token: cardToken,
      payment_method_id: paymentMethodId,
      installments: 1,
      idempotency_key: idempotencyKey,
      identification_type: identificationType,
      identification_number: identificationNumber,
    };

    checkoutOnlineMutation.mutate(payload);
  }

  function handleCheckoutPickupEfectivo() {
    const payload: CheckoutPickupEfectivoRequest = {
      items: buildCheckoutItems(),
      notas: notas.trim() || null,
    };

    checkoutPickupMutation.mutate(payload);
  }

  function handleSubmit() {
    if (!selectedPaymentMethod) {
      toast.error('Seleccioná una forma de pago');
      return;
    }

    if (selectedPaymentMethod === 'MERCADOPAGO') {
      handleCheckoutOnline();
    } else if (selectedPaymentMethod === 'EFECTIVO') {
      handleCheckoutPickupEfectivo();
    }
  }

  const isProcessing = checkoutOnlineMutation.isPending || checkoutPickupMutation.isPending;
  const isOnlinePaymentReady = cardToken && paymentMethodId && identificationNumber;
  const isSubmitDisabled =
    !selectedPaymentMethod ||
    isProcessing ||
    (selectedPaymentMethod === 'MERCADOPAGO' && !isOnlinePaymentReady);

  // Show PaymentForm when MERCADOPAGO is selected
  const showPaymentForm = selectedPaymentMethod === 'MERCADOPAGO';

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
          Revisá los datos de tu pedido y completá el pago
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
              isDelivery={isDelivery}
            />
          </div>

          {/* Inline PaymentForm for MERCADOPAGO */}
          {showPaymentForm && (
            <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-5 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Datos de la tarjeta</h3>
              <SecureCardForm
                onSubmit={(token, methodId, idType, idNumber) => {
                  setCardToken(token);
                  setPaymentMethodId(methodId);
                  setIdentificationType(idType);
                  setIdentificationNumber(idNumber);
                }}
                onError={(message) => {
                  toast.error('Error en la tarjeta', { description: message });
                }}
                isLoading={isProcessing}
              />
            </div>
          )}
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
            isLoading={isProcessing}
            className="w-full"
          >
            {isProcessing
              ? 'Procesando...'
              : selectedPaymentMethod === 'MERCADOPAGO'
              ? 'Confirmar y pagar'
              : 'Confirmar pedido'}
          </Button>

          {!selectedPaymentMethod && (
            <p className="text-xs text-center text-muted-foreground">
              Seleccioná una forma de pago para continuar
            </p>
          )}

          {selectedPaymentMethod === 'MERCADOPAGO' && !isOnlinePaymentReady && (
            <p className="text-xs text-center text-muted-foreground">
              Completá los datos de la tarjeta para continuar
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
