import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type { ProfileRead, UpdateProfilePayload, ChangePasswordPayload } from '../types/userProfile.types';

export async function getProfile(): Promise<ProfileRead> {
  const response = await apiClient.get<ProfileRead>(ENDPOINTS.usuarios.me);
  return response.data;
}

export async function updateProfile(data: UpdateProfilePayload): Promise<ProfileRead> {
  const response = await apiClient.patch<ProfileRead>(ENDPOINTS.usuarios.me, data);
  return response.data;
}

export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await apiClient.post(ENDPOINTS.usuarios.password, payload);
}
