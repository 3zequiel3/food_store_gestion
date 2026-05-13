import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { deleteCategoria } from '../services/categorias.service';
import { ApiError } from '../../../api/interceptors/error';

export function useDeleteCategoria(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteCategoria(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
      toast.success('Categoría eliminada');
      onSuccess?.();
    },
    onError(error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error('No se puede eliminar', {
          description: 'La categoría tiene subcategorías o productos asociados.',
        });
        return;
      }
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al eliminar categoría', { description: msg ?? undefined });
    },
  });
}
