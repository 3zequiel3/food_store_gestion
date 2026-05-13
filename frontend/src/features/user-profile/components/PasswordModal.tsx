import { useEffect, useRef } from 'react';
import { useForm } from '@tanstack/react-form';
import { X } from 'lucide-react';
import { useChangePassword } from '../hooks/useChangePassword';
import { passwordSchema } from '../schemas/passwordSchema';
import { ApiError } from '../../../api/interceptors/error';

interface PasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PasswordModal({ isOpen, onClose }: PasswordModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const { mutate, isPending, error, reset } = useChangePassword();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  const form = useForm({
    defaultValues: {
      password_actual: '',
      password_nuevo: '',
    },
    onSubmit: async ({ value }) => {
      mutate(value);
    },
  });

  function handleClose() {
    form.reset();
    reset();
    onClose();
  }

  const backendError = error instanceof ApiError
    ? (error.status === 401 ? 'Credenciales inválidas' : (error.detail || 'Ocurrió un error. Intentá de nuevo.'))
    : null;

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      aria-labelledby="password-modal-title"
      className="
        w-full max-w-md rounded-xl border border-border bg-card p-0 shadow-xl
        backdrop:bg-black/50 backdrop:backdrop-blur-sm
        open:animate-in open:fade-in open:zoom-in-95
      "
    >
      <div className="flex flex-col gap-5 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 id="password-modal-title" className="text-lg font-semibold text-foreground">
            Cambiar contraseña
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            aria-label="Cerrar modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {backendError && (
          <div
            role="alert"
            className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
          >
            {backendError}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            form.handleSubmit();
          }}
          className="flex flex-col gap-4"
          noValidate
        >
          {/* Contraseña actual */}
          <form.Field
            name="password_actual"
            validators={{
              onBlur: ({ value }) => {
                const r = passwordSchema.shape.password_actual.safeParse(value);
                return r.success ? undefined : r.error.issues[0]?.message;
              },
            }}
          >
            {(field) => (
              <div className="flex flex-col gap-1.5">
                <label htmlFor={field.name} className="text-sm font-medium text-foreground">
                  Contraseña actual
                </label>
                <input
                  id={field.name}
                  name={field.name}
                  type="password"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  autoComplete="current-password"
                  disabled={isPending}
                  className="h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full"
                />
                {field.state.meta.errors.length > 0 && (
                  <p role="alert" className="text-xs text-destructive">
                    {field.state.meta.errors.join(', ')}
                  </p>
                )}
              </div>
            )}
          </form.Field>

          {/* Nueva contraseña */}
          <form.Field
            name="password_nuevo"
            validators={{
              onBlur: ({ value }) => {
                const r = passwordSchema.shape.password_nuevo.safeParse(value);
                return r.success ? undefined : r.error.issues[0]?.message;
              },
            }}
          >
            {(field) => (
              <div className="flex flex-col gap-1.5">
                <label htmlFor={field.name} className="text-sm font-medium text-foreground">
                  Nueva contraseña
                </label>
                <input
                  id={field.name}
                  name={field.name}
                  type="password"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  autoComplete="new-password"
                  disabled={isPending}
                  placeholder="Mínimo 8 caracteres"
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

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={handleClose}
              disabled={isPending}
              className="flex-1 h-11 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-accent transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 h-11 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isPending ? (
                <>
                  <span
                    className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin"
                    aria-hidden="true"
                  />
                  Guardando…
                </>
              ) : (
                'Cambiar contraseña'
              )}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
