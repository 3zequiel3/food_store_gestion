import { z } from 'zod';

/**
 * Schema de validación para el formulario de registro.
 * Errores en español (RN: mensajes del sistema en español).
 */
export const registerSchema = z.object({
  nombre: z
    .string()
    .min(2, 'Mínimo 2 caracteres')
    .max(80, 'Máximo 80 caracteres'),
  apellido: z
    .string()
    .min(2, 'Mínimo 2 caracteres')
    .max(80, 'Máximo 80 caracteres'),
  email: z.string().email('Email inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
