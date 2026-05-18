import { describe, expect, it } from 'vitest';
import { friendlyMessageFor, statusDetailMessages } from '../statusDetailMessages';

describe('statusDetailMessages', () => {
  it('exports a record with at least the required MP status details', () => {
    const requiredKeys = [
      'cc_rejected_insufficient_amount',
      'cc_rejected_bad_filled_security_code',
      'cc_rejected_bad_filled_card_number',
      'cc_rejected_bad_filled_date',
      'cc_rejected_other_reason',
      'cc_rejected_call_for_authorize',
      'cc_rejected_high_risk',
      'pending_review_manual',
      'pending_waiting_payment',
      'accredited',
    ];
    for (const key of requiredKeys) {
      expect(statusDetailMessages).toHaveProperty(key);
      expect(typeof statusDetailMessages[key]).toBe('string');
    }
  });
});

describe('friendlyMessageFor', () => {
  it('retorna el mensaje mapeado cuando el status_detail es conocido', () => {
    const result = friendlyMessageFor('cc_rejected_insufficient_amount');
    expect(result).toBe('Saldo insuficiente. Probá con otra tarjeta.');
  });

  it('retorna el status_detail crudo cuando no está mapeado', () => {
    const result = friendlyMessageFor('cc_some_unknown_detail');
    expect(result).toBe('cc_some_unknown_detail');
  });

  it('retorna el fallback cuando es null', () => {
    const result = friendlyMessageFor(null);
    expect(result).toBe('Sin información adicional.');
  });

  it('retorna el fallback cuando es undefined', () => {
    const result = friendlyMessageFor(undefined);
    expect(result).toBe('Sin información adicional.');
  });

  it('retorna el mensaje de pending_review_manual correctamente', () => {
    const result = friendlyMessageFor('pending_review_manual');
    expect(result).toBe('Tu pago está en revisión. Te avisaremos cuando se confirme.');
  });
});
