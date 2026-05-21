import { useState, useEffect } from 'react';

export type UrgencyLevel = 'normal' | 'warning' | 'critical';

interface UrgencyResult {
  /** Minutos transcurridos desde la entrada a cocina. */
  elapsedMinutes: number;
  /** Nivel de urgencia según RN-CO07. */
  level: UrgencyLevel;
}

/**
 * Timer de urgencia para una orden de cocina.
 *
 * RN-CO07:
 * - < 10 min → normal (verde)
 * - 10–20 min → warning (naranja)
 * - > 20 min → critical (rojo)
 *
 * Recalcula cada 15 segundos.
 */
export function useUrgencyTimer(entradaCocinaAt: string | Date): UrgencyResult {
  const [result, setResult] = useState<UrgencyResult>(() =>
    computeUrgency(entradaCocinaAt),
  );

  useEffect(() => {
    const interval = setInterval(() => {
      setResult(computeUrgency(entradaCocinaAt));
    }, 15_000);

    return () => clearInterval(interval);
  }, [entradaCocinaAt]);

  return result;
}

function computeUrgency(entradaCocinaAt: string | Date): UrgencyResult {
  const entry = typeof entradaCocinaAt === 'string'
    ? new Date(entradaCocinaAt).getTime()
    : entradaCocinaAt.getTime();

  const now = Date.now();
  const elapsedMs = Math.max(0, now - entry);
  const elapsedMinutes = Math.floor(elapsedMs / 60_000);

  let level: UrgencyLevel;
  if (elapsedMinutes < 10) {
    level = 'normal';
  } else if (elapsedMinutes <= 20) {
    level = 'warning';
  } else {
    level = 'critical';
  }

  return { elapsedMinutes, level };
}
