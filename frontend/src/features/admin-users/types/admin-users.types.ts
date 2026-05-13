export interface AdminUserResponse {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  telefono: string | null;
  is_active: boolean;
  roles: string[];
  creado_en: string | null;
  actualizado_en: string | null;
}

export interface AdminUserListResponse {
  items: AdminUserResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUpdateUserRequest {
  nombre?: string;
  apellido?: string;
  telefono?: string | null;
}

export interface AdminChangeRolRequest {
  roles: string[];
}

export interface AdminChangeEstadoRequest {
  is_active: boolean;
}

export interface AdminUsersFilters {
  page: number;
  page_size?: number;
  search?: string;
  rol?: string;
}

export const ROLES = ['CLIENT', 'ADMIN', 'STOCK', 'PEDIDOS'] as const;
export type RolCode = (typeof ROLES)[number];
