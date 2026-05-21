import { Clock } from 'lucide-react';
import type { UrgencyLevel } from '../hooks/useUrgencyTimer';

interface UrgencyBadgeProps {
  elapsedMinutes: number;
  level: UrgencyLevel;
}

/**
 * Badge de urgencia que muestra el tiempo en cocina.
 *
 * Colores según RN-CO07:
 * - normal (< 10 min): texto muted-foreground
 * - warning (10–20 min): texto warning
 * - critical (> 20 min): texto destructive, con animación pulse
 */
export function UrgencyBadge({ elapsedMinutes, level }: UrgencyBadgeProps) {
  const colorMap: Record<UrgencyLevel, string> = {
    normal: 'text-muted-foreground',
    warning: 'text-warning',
    critical: 'text-destructive',
  };

  const pulse = level === 'critical' ? ' animate-pulse' : '';

  return (
    <span className={`flex items-center gap-1 text-xs font-mono font-semibold${colorMap[level]}${pulse}`}>
      <Clock className="h-3.5 w-3.5" />
      {elapsedMinutes} min
    </span>
  );
}
