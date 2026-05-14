import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createProduct } from '../services/admin-products.service';
import type { ProductoCreate, ProductoRead } from '../types/products.types';

export function useCreateProduct(onSuccess?: (data: ProductoRead) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProductoCreate) => createProduct(payload),
    onSuccess(data) {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      toast.success('Producto creado');
      onSuccess?.(data);
    },
    onError() {
      toast.error('Error al crear el producto');
    },
  });
}
