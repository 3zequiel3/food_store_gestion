import { Link } from 'react-router-dom';
import { LoginForm } from '../features/auth/components/LoginForm';

export function LoginPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background p-4">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-secondary/10" />
      <div className="pointer-events-none absolute top-1/4 -left-32 h-96 w-96 rounded-full bg-primary/5 blur-3xl" />
      <div className="pointer-events-none absolute bottom-1/4 -right-32 h-96 w-96 rounded-full bg-secondary/5 blur-3xl" />

      <div className="relative w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-primary">
            Food Store
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Ingresá a tu cuenta
          </p>
        </div>

        <div className="rounded-2xl bg-glass backdrop-blur-xl border border-glass-border p-6 shadow-xl min-h-[420px] flex flex-col justify-center">
          <LoginForm />

          <p className="mt-6 text-center text-sm text-muted-foreground">
            ¿No tenés cuenta?{' '}
            <Link
              to="/register"
              className="font-medium text-primary hover:text-primary/80 transition-colors"
            >
              Registrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
