import { useForm } from '@tanstack/react-form';
import { useNavigate } from 'react-router-dom';
import { useLogin } from '../hooks/useLogin';
import { loginSchema } from '../schemas/loginSchema';
import { ApiError } from '../../../api/interceptors/error';

/**
 * Formulario de login con TanStack Form + Zod (D-spec: NO react-hook-form).
 *
 * Validación: onBlur por defecto (R3: evitar lag en onChange).
 * Errores inline: 401 → "Credenciales inválidas" (spec 5.11).
 * Submit: deshabilitado durante isPending (spec 5.12).
 */
export function LoginForm() {
  const navigate = useNavigate();
  const { mutate: loginMutate, isPending, error } = useLogin();

  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      loginMutate(value, {
        onSuccess: () => navigate('/'),
      });
    },
  });

  // Extraer error de credenciales si viene del backend
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
      className="flex flex-col gap-4 w-full"
      noValidate
    >
      {/* Error general (no 401) */}
      {generalError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {generalError}
        </div>
      )}

      {/* Error credenciales (401) */}
      {credentialsError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {credentialsError}
        </div>
      )}

      {/* Campo email */}
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
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor={field.name}
              className="text-sm font-medium text-foreground"
            >
              Email
            </label>
            <input
              id={field.name}
              name={field.name}
              type="email"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              autoComplete="email"
              placeholder="tu@email.com"
              className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
              disabled={isPending}
            />
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      </form.Field>

      {/* Campo password */}
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
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor={field.name}
              className="text-sm font-medium text-foreground"
            >
              Contraseña
            </label>
            <input
              id={field.name}
              name={field.name}
              type="password"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              autoComplete="current-password"
              placeholder="••••••••"
              className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
              disabled={isPending}
            />
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      </form.Field>

      {/* Submit */}
      <button
        type="submit"
        disabled={isPending}
        className="h-11 w-full rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isPending ? (
          <>
            <span
              className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin"
              aria-hidden="true"
            />
            Ingresando…
          </>
        ) : (
          'Ingresar'
        )}
      </button>
    </form>
  );
}
