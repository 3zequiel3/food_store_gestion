import type { ReactNode } from 'react';

type BadgeVariant = 'success' | 'warning' | 'destructive' | 'info' | 'neutral' | 'primary';

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  success:
    'bg-success/15 text-success ring-1 ring-success/30',
  warning:
    'bg-warning/15 text-warning ring-1 ring-warning/30',
  destructive:
    'bg-destructive/15 text-destructive ring-1 ring-destructive/30',
  info:
    'bg-info/15 text-info ring-1 ring-info/30',
  neutral:
    'bg-muted text-muted-foreground ring-1 ring-border',
  primary:
    'bg-primary/15 text-primary ring-1 ring-primary/30',
};

export function Badge({ variant = 'neutral', className = '', children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
