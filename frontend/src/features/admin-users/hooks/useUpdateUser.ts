import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { updateUser } from '../services/admin-users.service';
import { ApiError } from '../../../api/interceptors/error';
import type { AdminUpdateUserRequest } from '../types/admin-users.types';

export function useUpdateUser(onClose?: () => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AdminUpdateUserRequest }) =>
      updateUser(id, payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success('Usuario actualizado');
      onClose?.();
    },
    onError(error) {
      const msg = error instanceof ApiError ? error.detail : 'Intentá de nuevo.';
      toast.error('Error al actualizar usuario', { description: msg ?? undefined });
    },
  });
}
