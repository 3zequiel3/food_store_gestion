import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { deleteProduct } from '../services/admin-products.service';

export function useDeleteProduct(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      toast.success('Producto eliminado');
      onSuccess?.();
    },
    onError() {
      toast.error('Error al eliminar el producto');
    },
  });
}
