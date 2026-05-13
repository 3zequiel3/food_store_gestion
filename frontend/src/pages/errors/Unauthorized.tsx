import { Link } from 'react-router-dom';

/**
 * Página 401 — Sesión expirada o no autenticado.
 * Reachable via route `path="/401"`.
 */
export function Unauthorized() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <div className="flex flex-col items-center gap-2">
        <span className="text-7xl font-bold text-muted-foreground/30">401</span>
        <h1 className="text-2xl font-bold text-foreground">
          Sesión expirada
        </h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Tu sesión expiró o no estás autenticado. Iniciá sesión para continuar.
        </p>
      </div>
      <Link
        to="/login"
        className="inline-flex h-11 items-center justify-center rounded-lg bg-primary px-6 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
      >
        Iniciar sesión
      </Link>
    </div>
  );
}
