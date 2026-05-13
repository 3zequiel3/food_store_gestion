import { Edit2, ShieldCheck, UserX, UserCheck } from 'lucide-react';
import type { AdminUserResponse } from '../types/admin-users.types';
import { UserStatusBadge } from './UserStatusBadge';
import { RoleBadge } from './RoleBadge';

interface AdminUserRowProps {
  user: AdminUserResponse;
  onEdit: (user: AdminUserResponse) => void;
  onChangeRol: (user: AdminUserResponse) => void;
  onToggleEstado: (user: AdminUserResponse) => void;
}

export function AdminUserRow({ user, onEdit, onChangeRol, onToggleEstado }: AdminUserRowProps) {
  return (
    <tr className="border-b border-border hover:bg-muted/30 transition-colors">
      <td className="px-4 py-3">
        <div>
          <p className="text-sm font-medium text-foreground">{user.nombre} {user.apellido}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {user.roles.map((rol) => (
            <RoleBadge key={rol} rol={rol} />
          ))}
        </div>
      </td>
      <td className="px-4 py-3">
        <UserStatusBadge isActive={user.is_active} />
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {user.creado_en ? new Date(user.creado_en).toLocaleDateString('es-AR') : '—'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onEdit(user)}
            title="Editar datos"
            className="p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            onClick={() => onChangeRol(user)}
            title="Cambiar roles"
            className="p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            <ShieldCheck className="h-4 w-4" />
          </button>
          <button
            onClick={() => onToggleEstado(user)}
            title={user.is_active ? 'Desactivar cuenta' : 'Activar cuenta'}
            className="p-1.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            {user.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
          </button>
        </div>
      </td>
    </tr>
  );
}
