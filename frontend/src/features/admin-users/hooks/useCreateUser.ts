import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createUser } from '../services/admin-users.service';
import type { AdminCreateUserRequest } from '../types/admin-users.types';

export function useCreateUser(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminCreateUserRequest) => createUser(payload),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      onSuccess?.();
    },
  });
}
