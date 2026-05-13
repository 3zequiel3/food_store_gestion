import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { IngredienteRead, PaginatedIngredientes, IngredienteCreate, IngredienteUpdate } from '../types/ingredientes.types';

export async function getIngredientes(page = 1, limit = 20): Promise<PaginatedIngredientes> {
  const response = await apiClient.get<PaginatedIngredientes>(ENDPOINTS.ingredientes.list, {
    params: { page, limit },
  });
  return response.data;
}

export async function getTodosIngredientes(): Promise<IngredienteRead[]> {
  const response = await apiClient.get<PaginatedIngredientes>(ENDPOINTS.ingredientes.list, {
    params: { page: 1, limit: 200 },
  });
  return response.data.items;
}

export async function createIngrediente(payload: IngredienteCreate): Promise<IngredienteRead> {
  const response = await apiClient.post<IngredienteRead>(ENDPOINTS.ingredientes.create, payload);
  return response.data;
}

export async function updateIngrediente(id: number, payload: IngredienteUpdate): Promise<IngredienteRead> {
  const response = await apiClient.put<IngredienteRead>(ENDPOINTS.ingredientes.update(id), payload);
  return response.data;
}

export async function deleteIngrediente(id: number): Promise<void> {
  await apiClient.delete(ENDPOINTS.ingredientes.delete(id));
}
