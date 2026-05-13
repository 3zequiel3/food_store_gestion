import { Construction } from 'lucide-react';

interface PlaceholderPageProps {
  title?: string;
  description?: string;
}

export function PlaceholderPage({
  title = 'En construcción',
  description = 'Esta sección estará disponible pronto.',
}: PlaceholderPageProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8">
      <div className="flex flex-col items-center gap-4 text-center max-w-sm">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-glass backdrop-blur-xl border border-glass-border shadow-sm">
          <Construction className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-xl font-bold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
