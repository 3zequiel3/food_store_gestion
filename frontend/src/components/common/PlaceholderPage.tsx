import type { ReactNode } from 'react';

interface PlaceholderPageProps {
  /** Título grande de la sección (ej. "Productos") */
  title: string;
  /** Texto secundario opcional (qué va a hacer la página cuando exista) */
  description?: string;
  /** Ícono opcional sobre el título — usar lucide-react o emoji */
  icon?: ReactNode;
}

/**
 * Página placeholder reutilizable mientras las features reales no están
 * implementadas. Los Sprints de Fase B reemplazan el `element` de la
 * Route por el componente real — no hace falta tocar el router.
 */
export function PlaceholderPage({
  title,
  description,
  icon = '🍳',
}: PlaceholderPageProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <div className="text-5xl">{icon}</div>
      <h2 className="text-2xl font-semibold text-foreground">{title}</h2>
      {description && (
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      <p className="text-xs uppercase tracking-wider text-muted-foreground/70">
        Próximamente — Fase B del roadmap
      </p>
    </div>
  );
}
