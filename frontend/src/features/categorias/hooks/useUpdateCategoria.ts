import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { updateCategoria } from '../services/categorias.service';
import { ApiError } from '../../../api/interceptors/error';
import type { CategoriaUpdate } from '../types/categorias.types';

export function useUpdateCategoria(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CategoriaUpdate }) =>
      updateCategoria(id, payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
      toast.success('Categoría actualizada');
      onSuccess?.();
    },
    onError(error) {
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al actualizar categoría', { description: msg ?? undefined });
    },
  });
}
