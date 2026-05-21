import { z } from 'zod';

/**
 * Schema de validación para el formulario de alta de usuarios desde admin.
 *
 * D8: 3 roles comunes con labels en español — ADMIN, CLIENT, COCINA.
 * STOCK y PEDIDOS se asignan con el PATCH /rol existente.
 */
export const createUserSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
  nombre: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  apellido: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  telefono: z.string().optional().or(z.literal('')),
  roles: z.array(z.string()).min(1, 'Seleccioná al menos un rol'),
});

export type CreateUserFormValues = z.infer<typeof createUserSchema>;
