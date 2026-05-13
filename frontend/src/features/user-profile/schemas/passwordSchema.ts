import { z } from 'zod';

export const passwordSchema = z.object({
  password_actual: z.string().min(1, 'Ingresá tu contraseña actual'),
  password_nuevo: z
    .string()
    .min(8, 'Mínimo 8 caracteres')
    .max(128, 'Máximo 128 caracteres'),
});

export type PasswordFormValues = z.infer<typeof passwordSchema>;
