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
      className="fixed bottom-0 left-0 right-0 z-20 flex h-16 bg-chrome backdrop-blur-xl border-t border-chrome-border md:hidden"
      aria-label="Navegación móvil"
    >
      {items.map((item) => {
        const isActive = item.path && location.pathname.startsWith(item.path);

        const content = (
          <>
            {isActive && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 h-0.5 w-8 rounded-full bg-primary" />
            )}
            <span
              className={`transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground'}`}
            >
              {item.icon}
            </span>
            <span
              className={`text-[10px] leading-tight transition-colors ${
                isActive ? 'text-primary font-semibold' : 'text-muted-foreground'
              }`}
            >
              {item.label}
            </span>
          </>
        );

        if (item.action) {
          return (
            <button
              key={item.label}
              type="button"
              onClick={item.action}
              className="relative flex flex-1 flex-col items-center justify-center gap-0.5 h-full min-w-[56px]"
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
            className="relative flex flex-1 flex-col items-center justify-center gap-0.5 h-full min-w-[56px]"
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
