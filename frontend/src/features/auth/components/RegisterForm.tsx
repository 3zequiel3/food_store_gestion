import { useForm } from '@tanstack/react-form';
import { useNavigate } from 'react-router-dom';
import { useRegister } from '../hooks/useRegister';
import { registerSchema } from '../schemas/registerSchema';
import { ApiError } from '../../../api/interceptors/error';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
            <Input
              id={field.name}
              name={field.name}
              type="text"
              label="Nombre"
              placeholder="Juan"
              autoComplete="given-name"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              error={field.state.meta.errors.join(', ') || undefined}
            />
          )}
        </form.Field>

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
            <Input
              id={field.name}
              name={field.name}
              type="text"
              label="Apellido"
              placeholder="Pérez"
              autoComplete="family-name"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              error={field.state.meta.errors.join(', ') || undefined}
            />
          )}
        </form.Field>
      </div>

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
            error={
              [field.state.meta.errors.join(', '), emailConflictError]
                .filter(Boolean)
                .join(', ') || undefined
            }
          />
        )}
      </form.Field>

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
          <Input
            id={field.name}
            name={field.name}
            type="password"
            label="Contraseña"
            placeholder="Mínimo 8 caracteres"
            autoComplete="new-password"
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
        {isPending ? 'Registrando…' : 'Crear cuenta'}
      </Button>
    </form>
  );
}
