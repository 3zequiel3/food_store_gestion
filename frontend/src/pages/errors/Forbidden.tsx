import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/Button';

export function Forbidden() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-destructive/5 via-transparent to-primary/5" />
      <div className="pointer-events-none absolute top-1/3 left-1/4 h-64 w-64 rounded-full bg-destructive/5 blur-3xl" />

      <div className="relative flex flex-col items-center gap-4">
        <span className="text-8xl font-bold bg-gradient-to-r from-destructive to-primary bg-clip-text text-transparent">
          403
        </span>
        <h1 className="text-2xl font-bold text-foreground">
          Acceso denegado
        </h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          No tenés permiso para ver esta página. Si creés que es un error, contactá al administrador.
        </p>
      </div>
      <Link to="/">
        <Button>Volver al inicio</Button>
      </Link>
    </div>
  );
}
