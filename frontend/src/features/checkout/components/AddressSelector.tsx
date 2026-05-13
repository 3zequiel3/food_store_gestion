import { MapPin, Store } from 'lucide-react';
import { useAddresses } from '../../delivery-addresses/hooks/useAddresses';
import type { DireccionRead } from '../../delivery-addresses/types/deliveryAddress.types';

interface AddressSelectorProps {
  selectedAddressId: number | null;
  onSelect: (addressId: number | null) => void;
}

export function AddressSelector({ selectedAddressId, onSelect }: AddressSelectorProps) {
  const { data: addresses, isLoading } = useAddresses();

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="font-semibold text-foreground">Dirección de entrega</h3>
        <div className="space-y-2">
          <div className="h-16 rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
          <div className="h-16 rounded-lg bg-gradient-to-r from-muted/50 via-muted to-muted/50 animate-shimmer bg-[length:200%_100%]" />
        </div>
      </div>
    );
  }

  const hasAddresses = addresses && addresses.length > 0;

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-foreground">Dirección de entrega</h3>

      <div className="space-y-2">
        <label
          className={`
            flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-150
            ${selectedAddressId === null
              ? 'border-primary bg-primary/10 shadow-sm shadow-primary/10'
              : 'border-glass-border bg-glass backdrop-blur-sm hover:bg-glass-hover'
            }
          `}
          onClick={() => onSelect(null)}
        >
          <input
            type="radio"
            name="deliveryAddress"
            checked={selectedAddressId === null}
            onChange={() => onSelect(null)}
            className="sr-only"
          />
          <div className={`
            h-5 w-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
            ${selectedAddressId === null ? 'border-primary' : 'border-muted-foreground'}
          `}>
            {selectedAddressId === null && <div className="h-2.5 w-2.5 rounded-full bg-primary" />}
          </div>
          <div className="flex items-center gap-3 flex-1">
            <Store className="h-5 w-5 text-muted-foreground" />
            <div className="flex-1">
              <p className="font-medium text-foreground">Retiro en local</p>
              <p className="text-xs text-muted-foreground">Sin costo de envío</p>
            </div>
          </div>
        </label>

        {hasAddresses && addresses.map((address: DireccionRead) => (
          <label
            key={address.id}
            className={`
              flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-150
              ${selectedAddressId === address.id
                ? 'border-primary bg-primary/10 shadow-sm shadow-primary/10'
                : 'border-glass-border bg-glass backdrop-blur-sm hover:bg-glass-hover'
              }
            `}
            onClick={() => onSelect(address.id)}
          >
            <input
              type="radio"
              name="deliveryAddress"
              checked={selectedAddressId === address.id}
              onChange={() => onSelect(address.id)}
              className="sr-only"
            />
            <div className={`
              h-5 w-5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              ${selectedAddressId === address.id ? 'border-primary' : 'border-muted-foreground'}
            `}>
              {selectedAddressId === address.id && (
                <div className="h-2.5 w-2.5 rounded-full bg-primary" />
              )}
            </div>
            <div className="flex items-center gap-3 flex-1">
              <MapPin className="h-5 w-5 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-foreground truncate">
                  {address.calle} {address.numero}
                  {address.es_principal && (
                    <span className="ml-2 text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                      Principal
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {address.ciudad}, CP {address.codigo_postal}
                </p>
                {(address.piso_depto || address.referencia) && (
                  <p className="text-xs text-muted-foreground truncate">
                    {address.piso_depto && `Piso/Depto: ${address.piso_depto}`}
                    {address.piso_depto && address.referencia && ' • '}
                    {address.referencia}
                  </p>
                )}
              </div>
            </div>
          </label>
        ))}

        {!hasAddresses && (
          <p className="text-sm text-muted-foreground px-1">
            No tenés direcciones guardadas. Podés agregar una desde{' '}
            <a href="/cliente/direcciones" className="text-primary hover:underline">
              Mis direcciones
            </a>
            {' '}o retirar en el local.
          </p>
        )}
      </div>
    </div>
  );
}
