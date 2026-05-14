import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { ProductoRead, ProductoCreate, ProductoUpdate, ImagenRead } from '../types/products.types';

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

// Image management functions

export async function getPresignedUploadUrl(id: number, contentType: string): Promise<{ url: string; fields: Record<string, string>; key: string }> {
  const response = await apiClient.post(`/productos/${id}/imagenes/presigned-url`, { content_type: contentType });
  return response.data;
}

export async function uploadProductImageDirect(id: number, file: File): Promise<string> {
  // 1. Get presigned POST from backend
  const { url, fields, key } = await getPresignedUploadUrl(id, file.type);

  // 2. Upload directly to S3 (bypasses backend entirely)
  const formData = new FormData();
  Object.entries(fields).forEach(([fKey, value]) => {
    formData.append(fKey, value);
  });
  formData.append('Content-Type', file.type);
  formData.append('file', file);

  console.log('[S3 Upload] Uploading to:', url);
  console.log('[S3 Upload] Content-Type:', file.type);

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('[S3 Upload] Failed:', response.status, errorText);
    throw new Error(`S3 upload failed: ${response.status} - ${errorText}`);
  }

  console.log('[S3 Upload] Success. Key:', key);
  return key;
}

export async function registerProductImage(id: number, key: string): Promise<ImagenRead> {
  const response = await apiClient.post<ImagenRead>(`/productos/${id}/imagenes/registro`, { key });
  return response.data;
}

// Legacy function — kept for STORAGE=local fallback
export async function uploadProductImage(id: number, file: File): Promise<ImagenRead> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<ImagenRead>(
    `/productos/${id}/imagenes`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
}

export async function addProductImageUrl(id: number, url: string): Promise<ImagenRead> {
  const response = await apiClient.post<ImagenRead>(`/productos/${id}/imagenes/url`, { url });
  return response.data;
}

export async function deleteProductImage(id: number, imagenId: number): Promise<void> {
  await apiClient.delete(`/productos/${id}/imagenes/${imagenId}`);
}

export async function setProductImagePrimary(id: number, imagenId: number): Promise<void> {
  await apiClient.patch(`/productos/${id}/imagenes/${imagenId}/primaria`);
}

export async function setProductImageOrder(id: number, imagenId: number, orden: number): Promise<void> {
  await apiClient.patch(`/productos/${id}/imagenes/${imagenId}/orden`, { orden });
}
