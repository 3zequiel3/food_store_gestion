import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { deleteIngrediente } from '../services/ingredientes.service';
import { ApiError } from '../../../api/interceptors/error';

export function useDeleteIngrediente(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteIngrediente(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['ingredientes'] });
      toast.success('Ingrediente eliminado');
      onSuccess?.();
    },
    onError(error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error('No se puede eliminar', {
          description: 'El ingrediente está asignado a uno o más productos.',
        });
        return;
      }
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al eliminar ingrediente', { description: msg ?? undefined });
    },
  });
}
