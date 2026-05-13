import { z } from 'zod';

const optionalStr = (max: number) =>
  z
    .string()
    .max(max)
    .transform((v) => (v.trim() === '' ? undefined : v.trim()))
    .optional();

export const addressSchema = z.object({
  calle: z.string().min(1, 'Requerido').max(255).trim(),
  numero: z.string().min(1, 'Requerido').max(20).trim(),
  ciudad: z.string().min(1, 'Requerido').max(100).trim(),
  codigo_postal: z.string().min(1, 'Requerido').max(20).trim(),
  piso_depto: optionalStr(50),
  referencia: optionalStr(255),
});

export type AddressFormValues = z.infer<typeof addressSchema>;
