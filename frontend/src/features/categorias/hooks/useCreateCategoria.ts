import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { createCategoria } from '../services/categorias.service';
import { ApiError } from '../../../api/interceptors/error';
import type { CategoriaCreate } from '../types/categorias.types';

export function useCreateCategoria(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CategoriaCreate) => createCategoria(payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['categorias'] });
      toast.success('Categoría creada');
      onSuccess?.();
    },
    onError(error) {
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al crear categoría', { description: msg ?? undefined });
    },
  });
}
