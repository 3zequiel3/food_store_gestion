import { useState } from 'react';
import { MapPin, Star, Pencil, Trash2 } from 'lucide-react';
import { useDeleteAddress } from '../hooks/useDeleteAddress';
import { useSetPrincipal } from '../hooks/useSetPrincipal';
import type { DireccionRead } from '../types/deliveryAddress.types';

interface AddressCardProps {
  address: DireccionRead;
  onEdit: (address: DireccionRead) => void;
  anyPending: boolean;
}

export function AddressCard({ address, onEdit, anyPending }: AddressCardProps) {
  const [confirming, setConfirming] = useState(false);
  const { mutate: deleteMutate, isPending: isDeleting } = useDeleteAddress();
  const { mutate: setPrincipalMutate, isPending: isSetting } = useSetPrincipal();

  const isPending = anyPending || isDeleting || isSetting;

  const line1 = [address.calle, address.numero, address.piso_depto]
    .filter(Boolean)
    .join(' ');
  const line2 = [address.ciudad, address.codigo_postal].filter(Boolean).join(', ');

  return (
    <div className={`relative flex flex-col gap-3 rounded-xl border p-4 transition-all duration-150 ${address.es_principal ? 'border-primary/30 bg-primary/5 shadow-sm shadow-primary/10' : 'border-glass-border bg-glass backdrop-blur-sm hover:bg-glass-hover'}`}>
      {address.es_principal && (
        <span className="inline-flex items-center gap-1 self-start rounded-full bg-primary px-2.5 py-0.5 text-xs font-semibold text-primary-foreground shadow-sm shadow-primary/30">
          <Star className="h-3 w-3" aria-hidden="true" />
          Predeterminada
        </span>
      )}

      <div className="flex items-start gap-3">
        <MapPin className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
        <div className="flex flex-col gap-0.5">
          <p className="text-sm font-medium text-foreground">{line1}</p>
          <p className="text-sm text-muted-foreground">{line2}</p>
          {address.referencia && (
            <p className="text-xs text-muted-foreground italic">{address.referencia}</p>
          )}
        </div>
      </div>

      {confirming ? (
        <div className="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2">
          <p className="flex-1 text-xs text-destructive font-medium">¿Eliminar esta dirección?</p>
          <button
            type="button"
            onClick={() => {
              deleteMutate(address.id);
              setConfirming(false);
            }}
            disabled={isDeleting}
            className="rounded-md bg-destructive px-2.5 py-1 text-xs font-semibold text-destructive-foreground hover:opacity-90 disabled:opacity-50"
          >
            {isDeleting ? 'Eliminando…' : 'Sí, eliminar'}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="rounded-md border border-glass-border px-2.5 py-1 text-xs font-medium text-foreground hover:bg-glass-hover transition-colors"
          >
            Cancelar
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {!address.es_principal && (
            <button
              type="button"
              onClick={() => setPrincipalMutate(address.id)}
              disabled={isPending}
              className="flex items-center gap-1.5 rounded-md border border-glass-border bg-glass backdrop-blur-sm px-3 py-1.5 text-xs font-medium text-foreground hover:bg-glass-hover transition-colors disabled:opacity-50"
            >
              <Star className="h-3 w-3" />
              Establecer como predeterminada
            </button>
          )}
          <button
            type="button"
            onClick={() => onEdit(address)}
            disabled={isPending}
            className="flex items-center gap-1.5 rounded-md border border-glass-border bg-glass backdrop-blur-sm px-3 py-1.5 text-xs font-medium text-foreground hover:bg-glass-hover transition-colors disabled:opacity-50"
          >
            <Pencil className="h-3 w-3" />
            Editar
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            disabled={isPending}
            className="flex items-center gap-1.5 rounded-md border border-destructive/30 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
          >
            <Trash2 className="h-3 w-3" />
            Eliminar
          </button>
        </div>
      )}
    </div>
  );
}
