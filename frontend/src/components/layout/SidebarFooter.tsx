import { LogOut } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { useLogout } from '../../features/auth/hooks/useLogout';

interface SidebarFooterProps {
  isExpanded: boolean;
}

export function SidebarFooter({ isExpanded }: SidebarFooterProps) {
  const user = useAuthStore((s) => s.user);
  const hasAdminRole = useAuthStore(
    (s) => s.hasRole('ADMIN') || s.hasRole('PEDIDOS') || s.hasRole('STOCK'),
  );
  const { mutate: logout } = useLogout();

  if (!user) return null;

  const initials = `${user.nombre.charAt(0)}${user.apellido.charAt(0)}`.toUpperCase();
  const profileRoute = hasAdminRole ? '/admin/usuarios' : '/cliente/perfil';

  return (
    <div className="border-t border-chrome-border/50 p-2">
      <Link
        to={profileRoute}
        className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-glass-hover"
        title={!isExpanded ? user.nombre : undefined}
      >
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-xs font-bold text-primary-foreground shadow-sm">
          {initials}
        </div>
        {isExpanded && (
          <span className="flex-1 truncate text-sm text-foreground/90">{user.nombre}</span>
        )}
      </Link>
      <button
        type="button"
        onClick={() => logout()}
        className={`mt-1 flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-colors hover:bg-glass-hover hover:text-destructive ${
          !isExpanded ? 'justify-center' : ''
        }`}
        aria-label="Cerrar sesión"
        title={!isExpanded ? 'Cerrar sesión' : undefined}
      >
        <LogOut className="h-4 w-4 flex-shrink-0" />
        {isExpanded && <span className="text-sm">Cerrar sesión</span>}
      </button>
    </div>
  );
}
