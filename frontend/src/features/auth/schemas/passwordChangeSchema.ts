import { z } from 'zod';

/**
 * Schema de validación para el cambio de contraseña.
 * Errores en español (RN: mensajes del sistema en español).
 */
export const passwordChangeSchema = z.object({
  current_password: z.string().min(1, 'Ingresá tu contraseña actual'),
  new_password: z.string().min(8, 'Mínimo 8 caracteres'),
});

export type PasswordChangeFormValues = z.infer<typeof passwordChangeSchema>;
