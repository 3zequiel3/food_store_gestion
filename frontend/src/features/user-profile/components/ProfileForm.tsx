import { useForm } from '@tanstack/react-form';
import { Check } from 'lucide-react';
import { useUpdateProfile } from '../hooks/useUpdateProfile';
import { profileSchema } from '../schemas/profileSchema';
import { ApiError } from '../../../api/interceptors/error';
import type { ProfileRead } from '../types/userProfile.types';

interface ProfileFormProps {
  profile: ProfileRead;
}

export function ProfileForm({ profile }: ProfileFormProps) {
  const { mutate, isPending, error, isSuccess } = useUpdateProfile();

  const form = useForm({
    defaultValues: {
      nombre: profile.nombre,
      apellido: profile.apellido,
      telefono: profile.telefono ?? '',
    },
    onSubmit: async ({ value }) => {
      const parsed = profileSchema.safeParse(value);
      if (!parsed.success) return;

      const { nombre, apellido, telefono } = parsed.data;
      mutate({ nombre, apellido, telefono });
    },
  });

  const backendError =
    error instanceof ApiError
      ? (error.detail || 'Ocurrió un error. Intentá de nuevo.')
      : null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        form.handleSubmit();
      }}
      className="flex flex-col gap-5"
      noValidate
    >
      {backendError && (
        <div
          role="alert"
          className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
        >
          {backendError}
        </div>
      )}

      {/* Email — solo lectura */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Email</label>
        <input
          type="email"
          value={profile.email}
          disabled
          className="h-11 rounded-lg border border-input bg-muted px-3 py-2 text-sm text-muted-foreground cursor-not-allowed w-full"
        />
        <p className="text-xs text-muted-foreground">El email no se puede cambiar.</p>
      </div>

      {/* Nombre */}
      <form.Field
        name="nombre"
        validators={{
          onBlur: ({ value }) => {
            const r = profileSchema.shape.nombre.safeParse(value);
            return r.success ? undefined : r.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={field.name} className="text-sm font-medium text-foreground">
              Nombre
            </label>
            <input
              id={field.name}
              name={field.name}
              type="text"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
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
            const r = profileSchema.shape.apellido.safeParse(value);
            return r.success ? undefined : r.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={field.name} className="text-sm font-medium text-foreground">
              Apellido
            </label>
            <input
              id={field.name}
              name={field.name}
              type="text"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
            />
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      </form.Field>

      {/* Teléfono */}
      <form.Field
        name="telefono"
        validators={{
          onBlur: ({ value }) => {
            if (!value || value.trim() === '') return undefined;
            const r = profileSchema.shape.telefono.safeParse(value);
            return r.success ? undefined : r.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={field.name} className="text-sm font-medium text-foreground">
              Teléfono <span className="text-muted-foreground font-normal">(opcional)</span>
            </label>
            <input
              id={field.name}
              name={field.name}
              type="tel"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              placeholder="+54 11 1234-5678"
              className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
            />
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      </form.Field>

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
            Guardando…
          </>
        ) : isSuccess ? (
          <>
            <Check className="h-4 w-4" />
            Guardado
          </>
        ) : (
          'Guardar cambios'
        )}
      </button>
    </form>
  );
}
