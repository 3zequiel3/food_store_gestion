import { Link } from 'react-router-dom';
import { LoginForm } from '../features/auth/components/LoginForm';

/**
 * Página de login — wrapper de presentación para LoginForm.
 * Centrada vertical y horizontalmente, card con max-w para desktop.
 */
export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">Food Store</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ingresá a tu cuenta
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-md">
          <LoginForm />

          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿No tenés cuenta?{' '}
            <Link
              to="/register"
              className="font-medium text-primary hover:underline"
            >
              Registrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
