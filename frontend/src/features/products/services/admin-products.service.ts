import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { ProductoRead, ProductoCreate, ProductoUpdate } from '../types/products.types';

export async function createProduct(payload: ProductoCreate): Promise<ProductoRead> {
  const response = await apiClient.post<ProductoRead>(ENDPOINTS.productos.create, payload);
  return response.data;
}

export async function updateProduct(id: number, payload: ProductoUpdate): Promise<ProductoRead> {
  const response = await apiClient.put<ProductoRead>(ENDPOINTS.productos.update(id), payload);
  return response.data;
}

export async function deleteProduct(id: number): Promise<void> {
  await apiClient.delete(ENDPOINTS.productos.delete(id));
}

export async function toggleDisponibilidad(id: number): Promise<ProductoRead> {
  const response = await apiClient.patch<ProductoRead>(ENDPOINTS.productos.disponibilidad(id));
  return response.data;
}

export async function updateStock(id: number, stock_cantidad: number): Promise<ProductoRead> {
  const response = await apiClient.patch<ProductoRead>(ENDPOINTS.productos.stock(id), { stock_cantidad });
  return response.data;
}
