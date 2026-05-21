import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingBag, ArrowLeft, MapPin, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { AddressSelector } from './AddressSelector';
import { PaymentMethodSelector } from './PaymentMethodSelector';
import { OrderSummaryPanel } from './OrderSummaryPanel';
import { SecureCardForm } from '../../payments/components/SecureCardForm';
import { useCheckoutOnline } from '../hooks/useCheckoutOnline';
import { useCheckoutPickupEfectivo } from '../hooks/useCheckoutPickupEfectivo';
import { useCartStore } from '../../cart/stores/cartStore';
import { useAuthStore } from '../../auth/stores/authStore';
import type {
  CheckoutItem,
  CheckoutOnlineRequest,
  CheckoutPickupEfectivoRequest,
} from '../types/checkout.types';

export function CheckoutPage() {
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);
  const userEmail = useAuthStore((s) => s.user?.email ?? '');

  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<string | null>(null);
  const [notas, setNotas] = useState('');
  const [idempotencyKey] = useState<string>(() => crypto.randomUUID());

  const cardFormRef = useRef<HTMLFormElement | null>(null);

  const checkoutOnlineMutation = useCheckoutOnline();
  const checkoutPickupMutation = useCheckoutPickupEfectivo();

  const isDelivery = selectedAddressId !== null;

  useEffect(() => {
    if (isDelivery && selectedPaymentMethod === 'EFECTIVO') {
      setSelectedPaymentMethod(null);
      toast.info('Efectivo no disponible para envíos', {
        description: 'Seleccioná otra forma de pago.',
      });
    }
  }, [isDelivery, selectedPaymentMethod]);

  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto py-20 px-4 text-center">
        <div className="flex justify-center mb-6">
          <div className="h-20 w-20 rounded-2xl bg-glass backdrop-blur-xl border border-glass-border flex items-center justify-center">
            <ShoppingBag className="h-9 w-9 text-muted-foreground/50" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-foreground mb-2">Tu carrito está vacío</h1>
        <p className="text-muted-foreground mb-6">Agregá productos del catálogo para continuar.</p>
        <button
          type="button"
          onClick={() => navigate('/cliente/catalogo')}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Ir al catálogo
        </button>
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

  function handleCheckoutOnline(token: string, methodId: string, idType: string, idNumber: string) {
    const payload: CheckoutOnlineRequest = {
      items: buildCheckoutItems(),
      tipo_entrega: isDelivery ? 'DELIVERY' : 'PICKUP',
      direccion_id: selectedAddressId,
      notas: notas.trim() || null,
      card_token: token,
      payment_method_id: methodId,
      installments: 1,
      idempotency_key: idempotencyKey,
      identification_type: idType,
      identification_number: idNumber,
      payer_email: userEmail,
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
    if (selectedPaymentMethod === 'TARJETA') {
      cardFormRef.current?.requestSubmit();
    } else if (selectedPaymentMethod === 'EFECTIVO') {
      handleCheckoutPickupEfectivo();
    }
  }

  const isProcessing = checkoutOnlineMutation.isPending || checkoutPickupMutation.isPending;
  const isSubmitDisabled = !selectedPaymentMethod || isProcessing;
  const showCardForm = selectedPaymentMethod === 'TARJETA';

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="mb-8">
          <button
            type="button"
            onClick={() => navigate('/cliente/catalogo')}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-5"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver al catálogo
          </button>
          <h1 className="text-2xl font-bold text-foreground">Finalizar compra</h1>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6 items-start">

          {/* LEFT — forms */}
          <div className="space-y-4">

            {/* Section 1 — Entrega */}
            <section className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 border-b border-glass-border">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground shrink-0">
                  1
                </span>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold text-foreground tracking-wide uppercase">
                    Entrega
                  </h2>
                </div>
              </div>
              <div className="p-5">
                <AddressSelector
                  selectedAddressId={selectedAddressId}
                  onSelect={setSelectedAddressId}
                />
              </div>
            </section>

            {/* Section 2 — Pago */}
            <section className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4 border-b border-glass-border">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground shrink-0">
                  2
                </span>
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold text-foreground tracking-wide uppercase">
                    Pago
                  </h2>
                </div>
              </div>
              <div className="p-5 space-y-5">
                <PaymentMethodSelector
                  selectedPaymentMethod={selectedPaymentMethod}
                  onSelect={setSelectedPaymentMethod}
                  isDelivery={isDelivery}
                />

                {showCardForm && (
                  <div className="border-t border-glass-border pt-5">
                    <p className="text-sm font-medium text-foreground mb-4">Datos de la tarjeta</p>
                    <SecureCardForm
                      formRef={cardFormRef}
                      onSubmit={(token, methodId, idType, idNumber) => {
                        handleCheckoutOnline(token, methodId, idType, idNumber);
                      }}
                      onError={(message) => {
                        toast.error('Error en la tarjeta', { description: message });
                      }}
                      isLoading={isProcessing}
                    />
                  </div>
                )}
              </div>
            </section>

            {/* Notes */}
            <section className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-5">
              <label htmlFor="notas" className="block text-sm font-medium text-foreground mb-2">
                Notas del pedido{' '}
                <span className="font-normal text-muted-foreground">(opcional)</span>
              </label>
              <textarea
                id="notas"
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Instrucciones especiales, alergias, referencias de entrega…"
                maxLength={500}
                rows={3}
                className="w-full px-3 py-2.5 text-sm bg-background/50 border border-glass-border rounded-lg text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all resize-none"
              />
              <p className="mt-1.5 text-xs text-muted-foreground text-right">{notas.length}/500</p>
            </section>
          </div>

          {/* RIGHT — sticky summary panel */}
          <div className="lg:sticky lg:top-20">
            <OrderSummaryPanel
              isLocalPickup={!isDelivery}
              isProcessing={isProcessing}
              isDisabled={isSubmitDisabled}
              onConfirm={handleSubmit}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
