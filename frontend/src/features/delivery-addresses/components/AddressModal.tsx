import { useEffect, useRef } from 'react';
import { useForm } from '@tanstack/react-form';
import { X } from 'lucide-react';
import { useCreateAddress } from '../hooks/useCreateAddress';
import { useUpdateAddress } from '../hooks/useUpdateAddress';
import { addressSchema } from '../schemas/addressSchema';
import { ApiError } from '../../../api/interceptors/error';
import type { DireccionRead } from '../types/deliveryAddress.types';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';

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
          <Input
            id={field.name}
            name={field.name}
            type="text"
            label={label + (!opts.required ? ' (opcional)' : '')}
            placeholder={opts.placeholder}
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            disabled={isPending}
            error={field.state.meta.errors.join(', ') || undefined}
          />
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
        m-auto w-full max-w-lg rounded-xl bg-white border border-gray-200 p-0 shadow-xl
        backdrop:bg-black/60 backdrop:backdrop-blur-sm
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
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
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
              {isPending ? 'Guardando…' : isEditing ? 'Guardar cambios' : 'Agregar dirección'}
            </Button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
