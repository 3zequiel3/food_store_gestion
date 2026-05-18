/**
 * Mapping of MercadoPago status_detail codes to user-friendly messages in Rioplatense Spanish.
 *
 * Design decision D7: simple Record constant, no i18n framework.
 * Add new entries as MP documents new status_detail values.
 */
export const statusDetailMessages: Record<string, string> = {
  cc_rejected_insufficient_amount: 'Saldo insuficiente. Probá con otra tarjeta.',
  cc_rejected_bad_filled_security_code: 'CVV incorrecto. Revisá el código de seguridad.',
  cc_rejected_bad_filled_card_number: 'Número de tarjeta incorrecto.',
  cc_rejected_bad_filled_date: 'Fecha de vencimiento incorrecta.',
  cc_rejected_other_reason: 'Tarjeta rechazada. Probá con otra.',
  cc_rejected_call_for_authorize: 'Tenés que autorizar el pago con tu banco.',
  cc_rejected_high_risk: 'Pago rechazado por seguridad. Probá con otra tarjeta.',
  pending_review_manual: 'Tu pago está en revisión. Te avisaremos cuando se confirme.',
  pending_waiting_payment: 'Tu pago está pendiente de procesamiento.',
  accredited: 'Pago aprobado.',
};

/**
 * Returns a user-friendly message for a given MP status_detail.
 *
 * - Known detail → mapped message in Spanish.
 * - Unknown truthy detail → return the raw status_detail as fallback.
 * - null / undefined → generic "Sin información adicional." fallback.
 */
export function friendlyMessageFor(statusDetail: string | null | undefined): string {
  if (!statusDetail) return 'Sin información adicional.';
  return statusDetailMessages[statusDetail] ?? statusDetail;
}
