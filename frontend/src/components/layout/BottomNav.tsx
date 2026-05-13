import { Link, useLocation } from 'react-router-dom';
import {
  Package,
  ClipboardList,
  Users,
  BarChart3,
  MoreHorizontal,
  ShoppingBag,
  ListOrdered,
  MapPin,
  User,
} from 'lucide-react';
import { useAuthStore } from '../../features/auth/stores/authStore';

interface BottomNavProps {
  onMoreOpen: () => void;
}

interface BottomNavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  action?: () => void;
}

/**
 * D3 — Mobile bottom navigation bar.
 * Fixed bottom, visible solo en <md (md:hidden).
 * Touch targets: cada item h-14 (56px) para iOS HIG compliance.
 */
export function BottomNav({ onMoreOpen }: BottomNavProps) {
  const location = useLocation();
  const hasAdmin = useAuthStore((s) => s.hasRole('ADMIN'));
  const hasPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'));
  const hasStock = useAuthStore((s) => s.hasRole('STOCK'));

  const isAdmin = hasAdmin || hasPedidos || hasStock;

  const adminItems: BottomNavItem[] = [
    { label: 'Productos', path: '/admin/productos', icon: <Package className="h-6 w-6" /> },
    { label: 'Pedidos', path: '/admin/pedidos', icon: <ClipboardList className="h-6 w-6" /> },
    { label: 'Usuarios', path: '/admin/usuarios', icon: <Users className="h-6 w-6" /> },
    { label: 'Métricas', path: '/admin/metricas', icon: <BarChart3 className="h-6 w-6" /> },
    {
      label: 'Más',
      path: '',
      icon: <MoreHorizontal className="h-6 w-6" />,
      action: onMoreOpen,
    },
  ];

  const clientItems: BottomNavItem[] = [
    { label: 'Catálogo', path: '/cliente/catalogo', icon: <ShoppingBag className="h-6 w-6" /> },
    { label: 'Pedidos', path: '/cliente/pedidos', icon: <ListOrdered className="h-6 w-6" /> },
    { label: 'Direcciones', path: '/cliente/direcciones', icon: <MapPin className="h-6 w-6" /> },
    { label: 'Perfil', path: '/cliente/perfil', icon: <User className="h-6 w-6" /> },
  ];

  const items = isAdmin ? adminItems : clientItems;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 flex h-16 bg-card border-t border-border md:hidden"
      aria-label="Navegación móvil"
    >
      {items.map((item) => {
        const isActive = item.path && location.pathname.startsWith(item.path);

        const content = (
          <>
            <span
              className={`transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground'}`}
            >
              {item.icon}
            </span>
            <span
              className={`text-xs transition-colors ${
                isActive ? 'text-primary font-medium' : 'text-muted-foreground'
              }`}
            >
              {item.label}
            </span>
          </>
        );

        // Items con action (el "Más")
        if (item.action) {
          return (
            <button
              key={item.label}
              type="button"
              onClick={item.action}
              className="flex flex-1 flex-col items-center justify-center gap-1 h-full min-w-[56px]"
              aria-label={item.label}
            >
              {content}
            </button>
          );
        }

        return (
          <Link
            key={item.path}
            to={item.path}
            className="flex flex-1 flex-col items-center justify-center gap-1 h-full min-w-[56px]"
            aria-label={item.label}
            aria-current={isActive ? 'page' : undefined}
          >
            {content}
          </Link>
        );
      })}
    </nav>
  );
}
