import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { changeRol } from '../services/admin-users.service';
import { ApiError } from '../../../api/interceptors/error';
import type { AdminChangeRolRequest } from '../types/admin-users.types';

export function useChangeRol(onClose?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AdminChangeRolRequest }) =>
      changeRol(id, payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success('Roles actualizados');
      onClose?.();
    },
    onError(error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error('No se puede quitar el último ADMIN activo del sistema.');
        return;
      }
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al cambiar roles', { description: msg ?? undefined });
    },
  });
}
