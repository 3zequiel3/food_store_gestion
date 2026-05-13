import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createIngrediente } from '../services/ingredientes.service';
import { ApiError } from '../../../api/interceptors/error';
import type { IngredienteCreate } from '../types/ingredientes.types';

export function useCreateIngrediente(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: IngredienteCreate) => createIngrediente(payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['ingredientes'] });
      toast.success('Ingrediente creado');
      onSuccess?.();
    },
    onError(error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error('Ya existe un ingrediente con ese nombre');
        return;
      }
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al crear ingrediente', { description: msg ?? undefined });
    },
  });
}
