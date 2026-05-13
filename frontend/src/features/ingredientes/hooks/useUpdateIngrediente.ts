import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { updateIngrediente } from '../services/ingredientes.service';
import { ApiError } from '../../../api/interceptors/error';
import type { IngredienteUpdate } from '../types/ingredientes.types';

export function useUpdateIngrediente(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: IngredienteUpdate }) =>
      updateIngrediente(id, payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['ingredientes'] });
      toast.success('Ingrediente actualizado');
      onSuccess?.();
    },
    onError(error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error('Ya existe un ingrediente con ese nombre');
        return;
      }
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al actualizar ingrediente', { description: msg ?? undefined });
    },
  });
}
