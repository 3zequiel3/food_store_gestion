import { useForm } from '@tanstack/react-form';
import { Check } from 'lucide-react';
import { useUpdateProfile } from '../hooks/useUpdateProfile';
import { profileSchema } from '../schemas/profileSchema';
import { ApiError } from '../../../api/interceptors/error';
import type { ProfileRead } from '../types/userProfile.types';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

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

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-foreground">Email</label>
        <input
          type="email"
          value={profile.email}
          disabled
          className="h-11 rounded-lg border border-glass-border bg-glass backdrop-blur-sm px-3 py-2 text-sm text-muted-foreground cursor-not-allowed w-full"
        />
        <p className="text-xs text-muted-foreground">El email no se puede cambiar.</p>
      </div>

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
          <Input
            id={field.name}
            name={field.name}
            type="text"
            label="Nombre"
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
            const r = profileSchema.shape.apellido.safeParse(value);
            return r.success ? undefined : r.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <Input
            id={field.name}
            name={field.name}
            type="text"
            label="Apellido"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            disabled={isPending}
            error={field.state.meta.errors.join(', ') || undefined}
          />
        )}
      </form.Field>

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
          <Input
            id={field.name}
            name={field.name}
            type="tel"
            label="Teléfono"
            placeholder="+54 11 1234-5678"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            disabled={isPending}
            helperText="Opcional"
            error={field.state.meta.errors.join(', ') || undefined}
          />
        )}
      </form.Field>

      <Button
        type="submit"
        size="lg"
        isLoading={isPending}
        className="w-full"
        rightIcon={isSuccess && !isPending ? <Check className="h-4 w-4" /> : undefined}
      >
        {isPending ? 'Guardando…' : isSuccess ? 'Guardado' : 'Guardar cambios'}
      </Button>
    </form>
  );
}
