import { Link } from 'react-router-dom';
import { RegisterForm } from '../features/auth/components/RegisterForm';

/**
 * Página de registro — wrapper de presentación para RegisterForm.
 */
export function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">Food Store</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Creá tu cuenta
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-md">
          <RegisterForm />

          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Ya tenés cuenta?{' '}
            <Link
              to="/login"
              className="font-medium text-primary hover:underline"
            >
              Ingresar
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
