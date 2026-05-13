import type { HTMLAttributes, ReactNode } from 'react';

type CardVariant = 'elevated' | 'outlined' | 'interactive' | 'glass';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const variantStyles: Record<CardVariant, string> = {
  elevated:
    'bg-card border border-border/50 shadow-md',
  outlined:
    'bg-transparent border border-border',
  interactive:
    'bg-glass backdrop-blur-xl border border-glass-border shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer',
  glass:
    'bg-glass backdrop-blur-xl border border-glass-border shadow-sm',
};

const paddingStyles: Record<string, string> = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export function Card({
  variant = 'glass',
  padding = 'md',
  className = '',
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-xl ${variantStyles[variant]} ${paddingStyles[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
