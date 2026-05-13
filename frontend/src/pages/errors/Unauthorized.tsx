import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/Button';

export function Unauthorized() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-warning/5 via-transparent to-primary/5" />
      <div className="pointer-events-none absolute top-1/3 left-1/4 h-64 w-64 rounded-full bg-warning/5 blur-3xl" />

      <div className="relative flex flex-col items-center gap-4">
        <span className="text-8xl font-bold bg-gradient-to-r from-warning to-primary bg-clip-text text-transparent">
          401
        </span>
        <h1 className="text-2xl font-bold text-foreground">
          Sesión expirada
        </h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Tu sesión expiró o no estás autenticado. Iniciá sesión para continuar.
        </p>
      </div>
      <Link to="/login">
        <Button>Iniciar sesión</Button>
      </Link>
    </div>
  );
}
