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

export interface AdminCreateUserRequest {
  email: string;
  password: string;
  nombre: string;
  apellido: string;
  telefono?: string | null;
  roles: string[];
}

export interface AdminUsersFilters {
  page: number;
  page_size?: number;
  search?: string;
  rol?: string;
}

export const ROLES = ['CLIENT', 'ADMIN', 'STOCK', 'PEDIDOS', 'COCINA'] as const;
export type RolCode = (typeof ROLES)[number];

/** Roles disponibles en el formulario de alta (D8: 3 roles comunes). */
export const CREATE_USER_ROLES = ['ADMIN', 'CLIENT', 'COCINA'] as const;
export type CreateUserRolCode = (typeof CREATE_USER_ROLES)[number];

/** Labels en español para el selector de roles del formulario de alta. */
export const ROL_LABELS: Record<string, string> = {
  ADMIN: 'Admin',
  CLIENT: 'Cliente',
  COCINA: 'Cocinero',
  STOCK: 'Stock',
  PEDIDOS: 'Pedidos',
};
