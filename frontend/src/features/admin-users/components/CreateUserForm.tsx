import { useEffect, useState } from 'react';
import { useForm } from '@tanstack/react-form';
import { X } from 'lucide-react';
import { useCreateUser } from '../hooks/useCreateUser';
import { createUserSchema } from '../schemas/createUserSchema';
import { CREATE_USER_ROLES, ROL_LABELS } from '../types/admin-users.types';

interface CreateUserFormProps {
  onClose: () => void;
}

/**
 * Formulario de alta de usuarios desde el panel de admin.
 *
 * Usa TanStack Form + Zod para validación.
 * Selector de 3 roles comunes (ADMIN, CLIENT, COCINA) con labels en español.
 * STOCK y PEDIDOS se asignan con el PATCH /rol existente.
 */
export function CreateUserForm({ onClose }: CreateUserFormProps) {
  const { mutate, isPending } = useCreateUser(onClose);
  const [generalError, setGeneralError] = useState<string | null>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
      nombre: '',
      apellido: '',
      telefono: '',
      roles: [] as string[],
    },
    onSubmit: async ({ value }) => {
      setGeneralError(null);
      const result = createUserSchema.safeParse(value);
      if (!result.success) {
        return;
      }

      mutate({
        email: value.email.trim(),
        password: value.password,
        nombre: value.nombre.trim(),
        apellido: value.apellido.trim(),
        telefono: value.telefono.trim() || null,
        roles: value.roles,
      });
    },
  });

  function toggleRole(role: string) {
    form.setFieldValue(
      'roles',
      (prev) =>
        prev.includes(role)
          ? prev.filter((r: string) => r !== role)
          : [...prev, role],
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-md p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Crear usuario</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-accent text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            form.handleSubmit();
          }}
          className="space-y-4"
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

          {/* Email */}
          <form.Field
            name="email"
            validators={{
              onBlur: ({ value }) => {
                const result = createUserSchema.shape.email.safeParse(value);
                return result.success ? undefined : result.error.issues[0]?.message;
              },
            }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Email
                </label>
                <input
                  id={field.name}
                  name={field.name}
                  type="email"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  disabled={isPending}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  placeholder="usuario@email.com"
                  autoComplete="email"
                />
                {field.state.meta.errors.length > 0 && (
                  <p className="text-xs text-destructive mt-1">
                    {field.state.meta.errors.join(', ')}
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
                const result = createUserSchema.shape.password.safeParse(value);
                return result.success ? undefined : result.error.issues[0]?.message;
              },
            }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Contraseña
                </label>
                <input
                  id={field.name}
                  name={field.name}
                  type="password"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  disabled={isPending}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  placeholder="Mínimo 8 caracteres"
                  autoComplete="new-password"
                />
                {field.state.meta.errors.length > 0 && (
                  <p className="text-xs text-destructive mt-1">
                    {field.state.meta.errors.join(', ')}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          {/* Nombre + Apellido */}
          <div className="grid grid-cols-2 gap-3">
            <form.Field
              name="nombre"
              validators={{
                onBlur: ({ value }) => {
                  const result = createUserSchema.shape.nombre.safeParse(value);
                  return result.success ? undefined : result.error.issues[0]?.message;
                },
              }}
            >
              {(field) => (
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Nombre
                  </label>
                  <input
                    id={field.name}
                    name={field.name}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    disabled={isPending}
                    className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-xs text-destructive mt-1">
                      {field.state.meta.errors.join(', ')}
                    </p>
                  )}
                </div>
              )}
            </form.Field>

            <form.Field
              name="apellido"
              validators={{
                onBlur: ({ value }) => {
                  const result = createUserSchema.shape.apellido.safeParse(value);
                  return result.success ? undefined : result.error.issues[0]?.message;
                },
              }}
            >
              {(field) => (
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Apellido
                  </label>
                  <input
                    id={field.name}
                    name={field.name}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    disabled={isPending}
                    className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-xs text-destructive mt-1">
                      {field.state.meta.errors.join(', ')}
                    </p>
                  )}
                </div>
              )}
            </form.Field>
          </div>

          {/* Teléfono */}
          <form.Field name="telefono">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Teléfono
                </label>
                <input
                  id={field.name}
                  name={field.name}
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  disabled={isPending}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  placeholder="Opcional"
                />
              </div>
            )}
          </form.Field>

          {/* Roles */}
          <form.Field
            name="roles"
            validators={{
              onChange: ({ value }) => {
                const result = createUserSchema.shape.roles.safeParse(value);
                return result.success ? undefined : result.error.issues[0]?.message;
              },
            }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Roles
                </label>
                <div className="flex flex-wrap gap-2">
                  {CREATE_USER_ROLES.map((role) => {
                    const selected = field.state.value.includes(role);
                    return (
                      <button
                        key={role}
                        type="button"
                        onClick={() => toggleRole(role)}
                        className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                          selected
                            ? 'bg-primary text-primary-foreground border-primary'
                            : 'border-border text-muted-foreground hover:bg-accent'
                        }`}
                      >
                        {ROL_LABELS[role]}
                      </button>
                    );
                  })}
                </div>
                {field.state.meta.errors.length > 0 && (
                  <p className="text-xs text-destructive mt-1">
                    {field.state.meta.errors.join(', ')}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {isPending ? 'Creando...' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
