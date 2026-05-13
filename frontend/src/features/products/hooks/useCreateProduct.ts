import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createProduct } from '../services/admin-products.service';
import type { ProductoCreate } from '../types/products.types';

export function useCreateProduct(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProductoCreate) => createProduct(payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      toast.success('Producto creado');
      onSuccess?.();
    },
    onError() {
      toast.error('Error al crear el producto');
    },
  });
}
