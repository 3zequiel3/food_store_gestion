import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';
import type {
  AdminUserListResponse,
  AdminUserResponse,
  AdminUpdateUserRequest,
  AdminChangeRolRequest,
  AdminChangeEstadoRequest,
  AdminUsersFilters,
} from '../types/admin-users.types';

export async function listUsers(filters: AdminUsersFilters): Promise<AdminUserListResponse> {
  const response = await apiClient.get<AdminUserListResponse>(ENDPOINTS.adminUsuarios.list, {
    params: {
      page: filters.page,
      page_size: filters.page_size ?? 20,
      ...(filters.search ? { search: filters.search } : {}),
      ...(filters.rol ? { rol: filters.rol } : {}),
    },
  });
  return response.data;
}

export async function updateUser(id: number, payload: AdminUpdateUserRequest): Promise<AdminUserResponse> {
  const response = await apiClient.put<AdminUserResponse>(ENDPOINTS.adminUsuarios.update(id), payload);
  return response.data;
}

export async function changeRol(id: number, payload: AdminChangeRolRequest): Promise<AdminUserResponse> {
  const response = await apiClient.patch<AdminUserResponse>(ENDPOINTS.adminUsuarios.cambiarRol(id), payload);
  return response.data;
}

export async function changeEstado(id: number, payload: AdminChangeEstadoRequest): Promise<AdminUserResponse> {
  const response = await apiClient.patch<AdminUserResponse>(ENDPOINTS.adminUsuarios.toggleEstado(id), payload);
  return response.data;
}
