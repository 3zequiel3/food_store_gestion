export interface StockIssue {
  producto_id: number;
  nombre: string;
  stockDisponible: number;
  disponible: boolean;
}

export interface PriceChange {
  producto_id: number;
  nombre: string;
  precioAnterior: number;
  precioNuevo: number;
}

export interface ValidationResult {
  stockIssues: StockIssue[];
  priceChanges: PriceChange[];
}
