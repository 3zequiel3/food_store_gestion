export interface MetricsDateFilter {
  desde?: string;
  hasta?: string;
}

export interface ResumenMetricas {
  total_ventas: string;
  total_pedidos: number;
  ticket_promedio: string;
  total_usuarios: number;
  periodo_desde: string | null;
  periodo_hasta: string | null;
}

export interface PuntoPeriodo {
  periodo: string;
  total_ventas: string;
  cantidad_pedidos: number;
}

export interface VentasPorPeriodoResponse {
  granularidad: string;
  puntos: PuntoPeriodo[];
}

export interface ProductoTop {
  producto_id: number;
  nombre: string;
  cantidad_total: number;
  ingreso_total: string;
}

export interface TopProductosResponse {
  top: number;
  productos: ProductoTop[];
}

export interface DistribucionEstado {
  estado_codigo: string;
  cantidad: number;
}

export interface PedidosPorEstadoResponse {
  distribucion: DistribucionEstado[];
}

export type Granularidad = 'dia' | 'semana' | 'mes';
