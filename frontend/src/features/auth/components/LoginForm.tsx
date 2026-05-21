import { useForm } from '@tanstack/react-form';
import { useNavigate, useLocation } from 'react-router-dom';
import { useLogin } from '../hooks/useLogin';
import { useAuthStore } from '../stores/authStore';
import { loginSchema } from '../schemas/loginSchema';
import { ApiError } from '../../../api/interceptors/error';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const { mutate: loginMutate, isPending, error } = useLogin();

  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      loginMutate(value, {
        onSuccess: () => {
          // D7 — COCINA users always redirect to /cocina after login.
          const user = useAuthStore.getState().user;
          if (user?.roles.includes('COCINA')) {
            navigate('/cocina', { replace: true });
            return;
          }
          // D5 — Consume location.state.from for post-login redirect.
          // PrivateRoute sets state.from = location.pathname on redirect.
          // Fallback to '/' if no saved destination (e.g. direct /login visit).
          const from = (location.state as { from?: string } | null)?.from ?? '/';
          navigate(from, { replace: true });
        },
      });
    },
  });

  const credentialsError =
    error instanceof ApiError && error.status === 401
      ? 'Credenciales inválidas'
      : null;

  const generalError =
    error instanceof ApiError && error.status !== 401
      ? (error.detail || 'Ocurrió un error. Intentá de nuevo.')
      : null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        form.handleSubmit();
      }}
      className="flex flex-col gap-5 w-full"
      noValidate
    >
      {generalError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {generalError}
        </div>
      )}

      {credentialsError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {credentialsError}
        </div>
      )}

      <form.Field
        name="email"
        validators={{
          onBlur: ({ value }) => {
            const result = loginSchema.shape.email.safeParse(value);
            return result.success ? undefined : result.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <Input
            id={field.name}
            name={field.name}
            type="email"
            label="Email"
            placeholder="tu@email.com"
            autoComplete="email"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            disabled={isPending}
            error={field.state.meta.errors.join(', ') || undefined}
          />
        )}
      </form.Field>

      <form.Field
        name="password"
        validators={{
          onBlur: ({ value }) => {
            const result = loginSchema.shape.password.safeParse(value);
            return result.success ? undefined : result.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <Input
            id={field.name}
            name={field.name}
            type="password"
            label="Contraseña"
            placeholder="••••••••"
            autoComplete="current-password"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            disabled={isPending}
            error={field.state.meta.errors.join(', ') || undefined}
          />
        )}
      </form.Field>

      <Button
        type="submit"
        size="lg"
        isLoading={isPending}
        className="w-full"
      >
        {isPending ? 'Ingresando…' : 'Ingresar'}
      </Button>
    </form>
  );
}
