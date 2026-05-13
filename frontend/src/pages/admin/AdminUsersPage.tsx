import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Users } from 'lucide-react';
import type { AdminUserResponse } from '../../features/admin-users/types/admin-users.types';
import { useAdminUsers } from '../../features/admin-users/hooks/useAdminUsers';
import { AdminUserFilters } from '../../features/admin-users/components/AdminUserFilters';
import { AdminUserRow } from '../../features/admin-users/components/AdminUserRow';
import { EditUserModal } from '../../features/admin-users/components/EditUserModal';
import { ChangeRolModal } from '../../features/admin-users/components/ChangeRolModal';
import { ToggleEstadoModal } from '../../features/admin-users/components/ToggleEstadoModal';

type ModalType = 'edit' | 'rol' | 'estado' | null;

const PAGE_SIZE = 20;

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="border-b border-border">
          {Array.from({ length: 5 }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 bg-muted rounded animate-pulse" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function AdminUsersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') ?? '1');
  const search = searchParams.get('search') ?? undefined;
  const rol = searchParams.get('rol') ?? undefined;

  const [selectedUser, setSelectedUser] = useState<AdminUserResponse | null>(null);
  const [modal, setModal] = useState<ModalType>(null);

  const { data, isLoading } = useAdminUsers({ page, page_size: PAGE_SIZE, search, rol });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  function openModal(user: AdminUserResponse, type: ModalType) {
    setSelectedUser(user);
    setModal(type);
  }

  function closeModal() {
    setSelectedUser(null);
    setModal(null);
  }

  function goToPage(p: number) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('page', String(p));
      return next;
    });
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Users className="h-6 w-6 text-muted-foreground" />
        <h1 className="text-2xl font-bold text-foreground">Usuarios</h1>
        {data && (
          <span className="text-sm text-muted-foreground">({data.total} en total)</span>
        )}
      </div>

      <AdminUserFilters />

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">Usuario</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">Roles</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">Estado</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">Registrado</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <SkeletonRows />}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground text-sm">
                  No se encontraron usuarios con los filtros actuales.
                </td>
              </tr>
            )}
            {!isLoading && data?.items.map((user) => (
              <AdminUserRow
                key={user.id}
                user={user}
                onEdit={(u) => openModal(u, 'edit')}
                onChangeRol={(u) => openModal(u, 'rol')}
                onToggleEstado={(u) => openModal(u, 'estado')}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-muted-foreground">
            Página {page} de {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => goToPage(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-accent disabled:opacity-40 transition-colors"
            >
              Anterior
            </button>
            <button
              onClick={() => goToPage(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-accent disabled:opacity-40 transition-colors"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}

      {/* Modales */}
      {selectedUser && modal === 'edit' && (
        <EditUserModal user={selectedUser} onClose={closeModal} />
      )}
      {selectedUser && modal === 'rol' && (
        <ChangeRolModal user={selectedUser} onClose={closeModal} />
      )}
      {selectedUser && modal === 'estado' && (
        <ToggleEstadoModal user={selectedUser} onClose={closeModal} />
      )}
    </div>
  );
}
