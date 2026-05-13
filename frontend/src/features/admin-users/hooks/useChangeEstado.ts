import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { changeEstado } from '../services/admin-users.service';
import { ApiError } from '../../../api/interceptors/error';
import type { AdminChangeEstadoRequest } from '../types/admin-users.types';

export function useChangeEstado(onClose?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AdminChangeEstadoRequest }) =>
      changeEstado(id, payload),
    onSuccess(data) {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success(data.is_active ? 'Usuario activado' : 'Usuario desactivado');
      onClose?.();
    },
    onError(error) {
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al cambiar estado', { description: msg ?? undefined });
    },
  });
}
