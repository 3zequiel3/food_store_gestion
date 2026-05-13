export type EstadoCodigo =
  | 'PENDIENTE'
  | 'CONFIRMADO'
  | 'EN_PREPARACION'
  | 'EN_CAMINO'
  | 'ENTREGADO'
  | 'CANCELADO';

export type FormaPagoCodigo = 'EFECTIVO' | 'MERCADOPAGO';

export interface PedidoListItem {
  id: number;
  estado_codigo: EstadoCodigo;
  total: string;
  costo_envio: string;
  forma_pago_codigo: FormaPagoCodigo;
  creado_en: string;
  items_count: number;
}

export interface PaginatedPedidos {
  items: PedidoListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface DetallePedidoItem {
  id: number;
  producto_id: number;
  nombre_snapshot: string;
  precio_snapshot: string;
  cantidad: number;
  personalizacion: number[] | null;
}

export interface HistorialEstado {
  id: number;
  estado_anterior_codigo: string | null;
  estado_nuevo_codigo: string;
  cambiado_por_id: number | null;
  motivo: string | null;
  creado_en: string;
}

export interface PagoInfo {
  id: number;
  status: string;
  monto: string;
  fecha: string;
}

export interface PedidoDetalle {
  id: number;
  user_id: number;
  estado_codigo: EstadoCodigo;
  total: string;
  costo_envio: string;
  forma_pago_codigo: FormaPagoCodigo;
  direccion_snapshot: string | null;
  notas: string | null;
  creado_en: string;
  actualizado_en: string | null;
  items: DetallePedidoItem[];
  historial: HistorialEstado[];
  pagos: PagoInfo[];
}

export interface OrderFilters {
  estado?: EstadoCodigo | '';
  desde?: string;
  hasta?: string;
  q?: string;
  page?: number;
  limit?: number;
}

export interface AvanzarEstadoRequest {
  nuevo_estado: EstadoCodigo;
  motivo?: string;
}
