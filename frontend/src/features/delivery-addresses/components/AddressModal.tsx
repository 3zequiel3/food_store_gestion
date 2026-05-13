import { useEffect, useRef } from 'react';
import { useForm } from '@tanstack/react-form';
import { X } from 'lucide-react';
import { useCreateAddress } from '../hooks/useCreateAddress';
import { useUpdateAddress } from '../hooks/useUpdateAddress';
import { addressSchema } from '../schemas/addressSchema';
import { ApiError } from '../../../api/interceptors/error';
import type { DireccionRead } from '../types/deliveryAddress.types';

interface AddressModalProps {
  isOpen: boolean;
  onClose: () => void;
  address?: DireccionRead;
}

const EMPTY = { calle: '', numero: '', ciudad: '', codigo_postal: '', piso_depto: '', referencia: '' };

export function AddressModal({ isOpen, onClose, address }: AddressModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const isEditing = !!address;

  const createMutation = useCreateAddress();
  const updateMutation = useUpdateAddress();

  const mutation = isEditing ? updateMutation : createMutation;
  const { isPending, error, reset: resetMutation } = mutation;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen) dialog.showModal();
    else dialog.close();
  }, [isOpen]);

  const form = useForm({
    defaultValues: address
      ? {
          calle: address.calle,
          numero: address.numero,
          ciudad: address.ciudad,
          codigo_postal: address.codigo_postal,
          piso_depto: address.piso_depto ?? '',
          referencia: address.referencia ?? '',
        }
      : EMPTY,
    onSubmit: async ({ value }) => {
      const parsed = addressSchema.safeParse(value);
      if (!parsed.success) return;
      const { calle, numero, ciudad, codigo_postal, piso_depto, referencia } = parsed.data;
      const payload = { calle, numero, ciudad, codigo_postal, piso_depto, referencia };

      if (isEditing) {
        (updateMutation as typeof updateMutation).mutate(
          { id: address.id, data: payload },
          { onSuccess: handleClose },
        );
      } else {
        (createMutation as typeof createMutation).mutate(payload as Parameters<typeof createMutation.mutate>[0], {
          onSuccess: handleClose,
        });
      }
    },
  });

  function handleClose() {
    form.reset();
    resetMutation();
    onClose();
  }

  const backendError = error instanceof ApiError
    ? (error.detail || 'Ocurrió un error. Intentá de nuevo.')
    : null;

  const fieldClass = 'h-11 rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 w-full';

  function renderField(
    name: keyof typeof EMPTY,
    label: string,
    opts: { placeholder?: string; required?: boolean } = {},
  ) {
    const schema = addressSchema.shape[name as keyof typeof addressSchema.shape];
    return (
      <form.Field
        name={name}
        validators={{
          onBlur: ({ value }) => {
            if (!schema) return undefined;
            const r = (schema as typeof schema).safeParse(value);
            return r.success ? undefined : r.error.issues[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={field.name} className="text-sm font-medium text-foreground">
              {label}
              {!opts.required && (
                <span className="text-muted-foreground font-normal"> (opcional)</span>
              )}
            </label>
            <input
              id={field.name}
              name={field.name}
              type="text"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              disabled={isPending}
              placeholder={opts.placeholder}
              className={fieldClass}
            />
            {field.state.meta.errors.length > 0 && (
              <p role="alert" className="text-xs text-destructive">
                {field.state.meta.errors.join(', ')}
              </p>
            )}
          </div>
        )}
      </form.Field>
    );
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      aria-labelledby="address-modal-title"
      className="
        w-full max-w-lg rounded-xl border border-border bg-card p-0 shadow-xl
        backdrop:bg-black/50 backdrop:backdrop-blur-sm
        open:animate-in open:fade-in open:zoom-in-95
      "
    >
      <div className="flex flex-col gap-4 p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 id="address-modal-title" className="text-lg font-semibold text-foreground">
            {isEditing ? 'Editar dirección' : 'Nueva dirección'}
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {backendError && (
          <div role="alert" className="rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive">
            {backendError}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); form.handleSubmit(); }}
          className="flex flex-col gap-4"
          noValidate
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">{renderField('calle', 'Calle', { required: true, placeholder: 'Av. Siempre Viva' })}</div>
            <div>{renderField('numero', 'Número', { required: true, placeholder: '742' })}</div>
            <div>{renderField('piso_depto', 'Piso/Depto', { placeholder: '3 B' })}</div>
            <div>{renderField('ciudad', 'Ciudad', { required: true, placeholder: 'Buenos Aires' })}</div>
            <div>{renderField('codigo_postal', 'Código postal', { required: true, placeholder: 'C1001' })}</div>
            <div className="col-span-2">{renderField('referencia', 'Referencia', { placeholder: 'Entre calles, timbre, etc.' })}</div>
          </div>

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
              className="flex-1 h-11 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isPending ? (
                <>
                  <span className="h-4 w-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" aria-hidden="true" />
                  Guardando…
                </>
              ) : (
                isEditing ? 'Guardar cambios' : 'Agregar dirección'
              )}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
