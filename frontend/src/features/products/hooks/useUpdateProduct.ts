import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { updateProduct } from '../services/admin-products.service';
import type { ProductoUpdate } from '../types/products.types';

export function useUpdateProduct(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductoUpdate }) =>
      updateProduct(id, payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      toast.success('Producto actualizado');
      onSuccess?.();
    },
    onError() {
      toast.error('Error al actualizar el producto');
    },
  });
}
