import { useEffect, useRef } from 'react';
import { useForm } from '@tanstack/react-form';
import { X } from 'lucide-react';
import { useChangePassword } from '../hooks/useChangePassword';
import { passwordSchema } from '../schemas/passwordSchema';
import { ApiError } from '../../../api/interceptors/error';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

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
        m-auto w-full max-w-md rounded-xl bg-white border border-gray-200 p-0 shadow-xl
        backdrop:bg-black/60 backdrop:backdrop-blur-sm
        open:animate-in open:fade-in open:zoom-in-95
      "
    >
      <div className="flex flex-col gap-5 p-6">
        <div className="flex items-center justify-between">
          <h2 id="password-modal-title" className="text-lg font-semibold text-foreground">
            Cambiar contraseña
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
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
              <Input
                id={field.name}
                name={field.name}
                type="password"
                label="Contraseña actual"
                autoComplete="current-password"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                disabled={isPending}
                error={field.state.meta.errors.join(', ') || undefined}
              />
            )}
          </form.Field>

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
              <Input
                id={field.name}
                name={field.name}
                type="password"
                label="Nueva contraseña"
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

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isPending}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              isLoading={isPending}
              className="flex-1"
            >
              {isPending ? 'Guardando…' : 'Cambiar contraseña'}
            </Button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
