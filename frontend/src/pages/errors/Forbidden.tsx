import { Link } from 'react-router-dom';

/**
 * Página 403 — Acceso denegado.
 * Reachable via route `path="/403"` o redirect desde RoleGuard.
 */
export function Forbidden() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <div className="flex flex-col items-center gap-2">
        <span className="text-7xl font-bold text-muted-foreground/30">403</span>
        <h1 className="text-2xl font-bold text-foreground">
          Acceso denegado
        </h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          No tenés permiso para ver esta página. Si creés que es un error, contactá al administrador.
        </p>
      </div>
      <Link
        to="/"
        className="inline-flex h-11 items-center justify-center rounded-lg bg-primary px-6 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
      >
        Volver al inicio
      </Link>
    </div>
  );
}
