export interface PagoCreate {
  pedido_id: number;
}

export interface PagoRead {
  id: number;
  pedido_id: number;
  monto: string; // Decimal serialized as string from backend
  forma_pago_codigo: string;
  mp_payment_id: string | null;
  mp_status: string | null;
  idempotency_key: string;
  creado_en: string;
  actualizado_en: string;
  init_point: string | null;
}
