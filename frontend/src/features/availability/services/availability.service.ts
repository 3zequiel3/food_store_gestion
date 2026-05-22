/**
 * REST client for the ingredient availability (Faltantes) feature.
 *
 * Uses the shared apiClient + ENDPOINTS pattern.
 */
import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { ShortageReportItem, ResolveRequest, ResolveResponse } from '../types/availability.types';

/**
 * GET /api/v1/availability/faltantes
 * Returns all open ingredient shortages (resuelto_en IS NULL).
 */
export async function getFaltantes(): Promise<ShortageReportItem[]> {
  const { data } = await apiClient.get<ShortageReportItem[]>(ENDPOINTS.availability.faltantes);
  return data;
}

/**
 * POST /api/v1/availability/faltantes/{ingrediente_id}/resolver
 * Marks ingredient as available and closes all open shortage rows.
 */
export async function resolverFaltante(
  ingredienteId: number,
  body: ResolveRequest = {},
): Promise<ResolveResponse> {
  const { data } = await apiClient.post<ResolveResponse>(
    ENDPOINTS.availability.resolver(ingredienteId),
    body,
  );
  return data;
}
