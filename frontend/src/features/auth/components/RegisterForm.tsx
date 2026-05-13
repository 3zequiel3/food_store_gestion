import { useForm } from '@tanstack/react-form';
import { useNavigate } from 'react-router-dom';
import { useRegister } from '../hooks/useRegister';
import { registerSchema } from '../schemas/registerSchema';
import { ApiError } from '../../../api/interceptors/error';

/**
 * Formulario de registro con TanStack Form + Zod (D-spec: NO react-hook-form).
 *
 * Validación: onBlur por defecto (R3).
 * Errores inline: 409 → error en campo email "Email ya registrado" (spec 5.14).
 * Submit: deshabilitado durante isPending (spec 5.12).
 */
export function RegisterForm() {
  const navigate = useNavigate();
  const { mutate: registerMutate, isPending, error } = useRegister();

  const form = useForm({
    defaultValues: {
      nombre: '',
      apellido: '',
      email: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      registerMutate(value, {
        onSuccess: () => navigate('/'),
      });
    },
  });

  // 409 → email duplicado (se muestra en el campo email)
  const emailConflictError =
    error instanceof ApiError && error.status === 409
      ? 'Este email ya está registrado'
      : null;

  const generalError =
    error instanceof ApiError && error.status !== 409
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
      {/* Error general */}
      {generalError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {generalError}
        </div>
      )}

      {/* Nombre + Apellido — dos columnas en md+ */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Nombre */}
        <form.Field
          name="nombre"
          validators={{
            onBlur: ({ value }) => {
              const result = registerSchema.shape.nombre.safeParse(value);
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
                Nombre
              </label>
              <input
                id={field.name}
                name={field.name}
                type="text"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                autoComplete="given-name"
                placeholder="Juan"
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

        {/* Apellido */}
        <form.Field
          name="apellido"
          validators={{
            onBlur: ({ value }) => {
              const result = registerSchema.shape.apellido.safeParse(value);
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
                Apellido
              </label>
              <input
                id={field.name}
                name={field.name}
                type="text"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                autoComplete="family-name"
                placeholder="Pérez"
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
      </div>

      {/* Email */}
      <form.Field
        name="email"
        validators={{
          onBlur: ({ value }) => {
            const result = registerSchema.shape.email.safeParse(value);
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
            {/* Error de campo Zod */}
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
            {/* Error 409 del backend — inline en el campo email */}
            {emailConflictError && (
              <p role="alert" className="text-xs text-destructive">
                {emailConflictError}
              </p>
            )}
          </div>
        )}
      </form.Field>

      {/* Password */}
      <form.Field
        name="password"
        validators={{
          onBlur: ({ value }) => {
            const result = registerSchema.shape.password.safeParse(value);
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
              autoComplete="new-password"
              placeholder="Mínimo 8 caracteres"
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
            Registrando…
          </>
        ) : (
          'Crear cuenta'
        )}
      </button>
    </form>
  );
}
