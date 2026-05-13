import { z } from 'zod';

const telefonoRegex = /^\+?[\d\s\-\(\)]{6,30}$/;

export const profileSchema = z.object({
  nombre: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  apellido: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  telefono: z
    .string()
    .transform((val) => (val.trim() === '' ? undefined : val))
    .pipe(
      z.union([
        z.undefined(),
        z.string().regex(telefonoRegex, 'Formato de teléfono inválido'),
      ]),
    )
    .optional(),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;
