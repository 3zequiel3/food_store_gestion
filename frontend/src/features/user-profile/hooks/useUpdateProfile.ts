import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateProfile } from '../services/userProfile.service';
import { useAuthStore } from '../../auth/stores/authStore';
import type { UpdateProfilePayload } from '../types/userProfile.types';

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateProfilePayload) => updateProfile(data),
    onSuccess(updatedProfile) {
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });

      // Actualizar authStore.user con los campos que Usuario tiene
      const current = useAuthStore.getState();
      if (current.user) {
        current.setSession({
          accessToken: current.accessToken!,
          refreshToken: current.refreshToken!,
          user: {
            ...current.user,
            nombre: updatedProfile.nombre,
            apellido: updatedProfile.apellido,
          },
        });
      }
    },
  });
}
