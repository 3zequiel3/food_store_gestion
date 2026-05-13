import { z } from 'zod';

/**
 * Schema de validación para el formulario de login.
 * Errores en español (RN: mensajes del sistema en español).
 */
export const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Ingresá tu contraseña'),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
