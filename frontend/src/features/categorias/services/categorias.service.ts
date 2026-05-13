import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { CategoriaRead, CategoriaTreeNode, CategoriaCreate, CategoriaUpdate } from '../types/categorias.types';

export async function getCategorias(): Promise<CategoriaTreeNode[]> {
  const response = await apiClient.get<CategoriaTreeNode[]>(ENDPOINTS.categorias.list);
  return response.data;
}

export async function getCategoriasHojas(): Promise<CategoriaRead[]> {
  const response = await apiClient.get<CategoriaRead[]>(ENDPOINTS.categorias.list, {
    params: { solo_hojas: true },
  });
  return response.data;
}

export async function createCategoria(payload: CategoriaCreate): Promise<CategoriaRead> {
  const response = await apiClient.post<CategoriaRead>(ENDPOINTS.categorias.create, payload);
  return response.data;
}

export async function updateCategoria(id: number, payload: CategoriaUpdate): Promise<CategoriaRead> {
  const response = await apiClient.put<CategoriaRead>(ENDPOINTS.categorias.update(id), payload);
  return response.data;
}

export async function deleteCategoria(id: number): Promise<void> {
  await apiClient.delete(ENDPOINTS.categorias.delete(id));
}
