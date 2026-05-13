export interface ProfileRead {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  telefono: string | null;
  roles: string[];
  creado_en: string;
  actualizado_en: string;
}

export interface UpdateProfilePayload {
  nombre?: string;
  apellido?: string;
  telefono?: string | null;
}

export interface ChangePasswordPayload {
  password_actual: string;
  password_nuevo: string;
}
