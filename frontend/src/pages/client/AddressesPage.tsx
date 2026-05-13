import { useState } from 'react';
import { MapPin, Plus } from 'lucide-react';
import { useAddresses } from '../../features/delivery-addresses/hooks/useAddresses';
import { AddressCard } from '../../features/delivery-addresses/components/AddressCard';
import { AddressModal } from '../../features/delivery-addresses/components/AddressModal';
import type { DireccionRead } from '../../features/delivery-addresses/types/deliveryAddress.types';

export function AddressesPage() {
  const { data: addresses, isLoading, isError, refetch } = useAddresses();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAddress, setEditingAddress] = useState<DireccionRead | undefined>();

  function handleEdit(address: DireccionRead) {
    setEditingAddress(address);
    setModalOpen(true);
  }

  function handleAdd() {
    setEditingAddress(undefined);
    setModalOpen(true);
  }

  function handleClose() {
    setModalOpen(false);
    setEditingAddress(undefined);
  }

  if (isLoading) return <AddressesSkeleton />;

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-sm text-muted-foreground">No se pudieron cargar tus direcciones.</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <MapPin className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Mis direcciones</h1>
            <p className="text-sm text-muted-foreground">Gestioná tus direcciones de entrega</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleAdd}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
        >
          <Plus className="h-4 w-4" />
          Agregar
        </button>
      </div>

      {/* Lista o estado vacío */}
      {!addresses || addresses.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <MapPin className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">No tenés direcciones guardadas</p>
            <p className="text-sm text-muted-foreground">Agregá una para poder hacer pedidos.</p>
          </div>
          <button
            type="button"
            onClick={handleAdd}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Plus className="h-4 w-4" />
            Agregar mi primera dirección
          </button>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {addresses.map((addr) => (
            <li key={addr.id}>
              <AddressCard
                address={addr}
                onEdit={handleEdit}
                anyPending={false}
              />
            </li>
          ))}
        </ul>
      )}

      <AddressModal
        isOpen={modalOpen}
        onClose={handleClose}
        address={editingAddress}
      />
    </div>
  );
}

function AddressesSkeleton() {
  return (
    <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-muted" />
          <div className="flex flex-col gap-2">
            <div className="h-4 w-36 rounded bg-muted" />
            <div className="h-3 w-48 rounded bg-muted" />
          </div>
        </div>
        <div className="h-9 w-24 rounded-lg bg-muted" />
      </div>
      {[...Array(3)].map((_, i) => (
        <div key={i} className="rounded-xl border border-border p-4 flex flex-col gap-3">
          <div className="h-4 w-48 rounded bg-muted" />
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="flex gap-2">
            <div className="h-8 w-24 rounded-md bg-muted" />
            <div className="h-8 w-20 rounded-md bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}
