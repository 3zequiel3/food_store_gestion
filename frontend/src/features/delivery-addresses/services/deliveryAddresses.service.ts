import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { DireccionRead, DireccionCreate, DireccionUpdate } from '../types/deliveryAddress.types';

export async function getAddresses(): Promise<DireccionRead[]> {
  const response = await apiClient.get<DireccionRead[]>(ENDPOINTS.direcciones.list);
  return response.data;
}

export async function createAddress(data: DireccionCreate): Promise<DireccionRead> {
  const response = await apiClient.post<DireccionRead>(ENDPOINTS.direcciones.create, data);
  return response.data;
}

export async function updateAddress(id: number, data: DireccionUpdate): Promise<DireccionRead> {
  const response = await apiClient.put<DireccionRead>(ENDPOINTS.direcciones.update(id), data);
  return response.data;
}

export async function deleteAddress(id: number): Promise<void> {
  await apiClient.delete(ENDPOINTS.direcciones.delete(id));
}

export async function setPrincipal(id: number): Promise<DireccionRead> {
  const response = await apiClient.patch<DireccionRead>(ENDPOINTS.direcciones.predeterminada(id));
  return response.data;
}
