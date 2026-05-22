/**
 * Types for the ingredient availability (Faltantes) feature.
 *
 * Match backend schemas in features/availability/schemas.py.
 */

/** One open shortage row from GET /api/v1/availability/faltantes. */
export interface ShortageReportItem {
  id: number;
  ingrediente_id: number;
  ingrediente_nombre: string | null;
  reportado_por: number;
  pedido_id: number;
  creado_en: string; // ISO 8601
  resuelto_en: string | null;
  resuelto_por: number | null;
}

/** Optional body for POST /availability/faltantes/{id}/resolver. */
export interface ResolveRequest {
  /** "ingrediente comprado" | "solucionado" */
  accion?: string;
}

/** Response from POST /availability/faltantes/{id}/resolver. */
export interface ResolveResponse {
  ok: boolean;
  ingrediente_id: number;
  rows_closed: number;
}
