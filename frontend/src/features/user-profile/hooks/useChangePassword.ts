import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { changePassword } from '../services/userProfile.service';
import { useAuthStore } from '../../auth/stores/authStore';
import type { ChangePasswordPayload } from '../types/userProfile.types';

export function useChangePassword() {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changePassword(payload),
    onSuccess() {
      useAuthStore.getState().clearSession();
      navigate('/login', { replace: true });
    },
  });
}
