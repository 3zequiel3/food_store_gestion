import { z } from 'zod';

/**
 * Zod schemas for checkout form validation.
 *
 * Mirrors backend validation in CrearPedidoRequest and ItemPedidoRequest:
 * - min 1 item, max 50
 * - cantidad >= 1
 * - forma_pago_codigo required
 * - direccion_id optional (null for retiro en local)
 * - notas max 500 chars
 * - extra fields forbidden
 */

const itemPedidoSchema = z.object({
  producto_id: z.number().int().positive('El ID de producto debe ser positivo'),
  cantidad: z.number().int().min(1, 'La cantidad debe ser al menos 1').max(999, 'La cantidad máxima es 999'),
  personalizacion: z.array(z.number().int().positive()).max(20, 'Máximo 20 ingredientes personalizados').nullable().default(null),
});

export const crearPedidoSchema = z.object({
  items: z.array(itemPedidoSchema)
    .min(1, 'El pedido debe tener al menos 1 item')
    .max(50, 'El pedido no puede tener más de 50 items'),
  forma_pago_codigo: z.string().min(1, 'Seleccioná una forma de pago').max(50),
  direccion_id: z.number().int().positive().nullable().default(null),
  notas: z.string().max(500, 'Las notas no pueden exceder 500 caracteres').nullable().default(null),
});

export type CrearPedidoFormValues = z.infer<typeof crearPedidoSchema>;
