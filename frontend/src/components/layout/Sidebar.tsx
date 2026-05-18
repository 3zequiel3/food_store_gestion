import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Utensils,
  ClipboardList,
  Users,
  BarChart3,
  ShoppingBag,
  ListOrdered,
  MapPin,
  User,
  ChevronRight,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { SidebarFooter } from './SidebarFooter';

interface NavSubItem {
  label: string;
  path: string;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  subItems?: NavSubItem[];
}

const ADMIN_NAV: NavItem[] = [
  {
    label: 'Comidas',
    path: '/admin/productos',
    icon: <Utensils className="h-5 w-5" />,
    subItems: [
      { label: 'Productos', path: '/admin/productos' },
      { label: 'Categorías', path: '/admin/categorias' },
      { label: 'Ingredientes', path: '/admin/ingredientes' },
    ],
  },
  {
    label: 'Pedidos',
    path: '/admin/pedidos',
    icon: <ClipboardList className="h-5 w-5" />,
  },
  {
    label: 'Usuarios',
    path: '/admin/usuarios',
    icon: <Users className="h-5 w-5" />,
  },
  {
    label: 'Métricas',
    path: '/admin/metricas',
    icon: <BarChart3 className="h-5 w-5" />,
  },
];

const CLIENT_NAV: NavItem[] = [
  {
    label: 'Catálogo',
    path: '/cliente/catalogo',
    icon: <ShoppingBag className="h-5 w-5" />,
  },
  {
    label: 'Mis Pedidos',
    path: '/cliente/pedidos',
    icon: <ListOrdered className="h-5 w-5" />,
  },
  {
    label: 'Direcciones',
    path: '/cliente/direcciones',
    icon: <MapPin className="h-5 w-5" />,
  },
  {
    label: 'Perfil',
    path: '/cliente/perfil',
    icon: <User className="h-5 w-5" />,
  },
];

interface SidebarItemProps {
  item: NavItem;
  isExpanded: boolean;
}

function SidebarItem({ item, isExpanded }: SidebarItemProps) {
  const location = useLocation();
  const hasSubItems = item.subItems && item.subItems.length > 0;

  const isActive = hasSubItems
    ? item.subItems!.some((sub) => location.pathname.startsWith(sub.path))
    : location.pathname.startsWith(item.path);

  const [subMenuOpen, setSubMenuOpen] = useState(isActive);

  const showSubMenu = isExpanded && hasSubItems && subMenuOpen;

  const handleClick = () => {
    if (hasSubItems && isExpanded) {
      setSubMenuOpen((prev) => !prev);
    }
  };

  const activeBar = isActive
    ? 'before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-5 before:w-0.5 before:rounded-full before:bg-primary before:shadow-sm before:shadow-primary/50'
    : '';

  const itemClasses = `
    relative flex items-center gap-3 rounded-lg px-3 h-10 w-full
    transition-all duration-150 cursor-pointer
    ${activeBar}
    ${isActive
      ? 'bg-primary/10 text-primary font-medium'
      : 'text-muted-foreground hover:bg-glass-hover hover:text-foreground'
    }
  `;

  return (
    <div>
      {hasSubItems ? (
        <button
          type="button"
          onClick={handleClick}
          className={itemClasses}
          title={!isExpanded ? item.label : undefined}
          aria-expanded={isExpanded && subMenuOpen}
        >
          <span className="flex-shrink-0">{item.icon}</span>

          {isExpanded && (
            <>
              <span className="flex-1 truncate text-sm">{item.label}</span>
              {subMenuOpen ? (
                <ChevronDown className="h-4 w-4 flex-shrink-0" />
              ) : (
                <ChevronRight className="h-4 w-4 flex-shrink-0" />
              )}
            </>
          )}
        </button>
      ) : (
        <Link
          to={item.path}
          className={itemClasses}
          title={!isExpanded ? item.label : undefined}
        >
          <span className="flex-shrink-0">{item.icon}</span>
          {isExpanded && (
            <span className="flex-1 truncate text-sm">{item.label}</span>
          )}
        </Link>
      )}

      {showSubMenu && (
        <div className="ml-8 mt-1 flex flex-col gap-0.5">
          {item.subItems!.map((sub) => (
            <Link
              key={sub.path}
              to={sub.path}
              className={`
                flex h-9 items-center rounded-md px-3 text-sm transition-all duration-150
                ${location.pathname === sub.path
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-glass-hover hover:text-foreground'
                }
              `}
            >
              {sub.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

type SidebarMode = 'hover' | 'locked-open' | 'locked-closed';

interface SidebarProps {
  onLockChange?: (isLockedOpen: boolean) => void;
}

export function Sidebar({ onLockChange }: SidebarProps) {
  const [mode, setMode] = useState<SidebarMode>('hover');
  const [mouseInside, setMouseInside] = useState(false);

  const isExpanded =
    mode === 'locked-open' || (mode === 'hover' && mouseInside);

  // D1 — Guard temprano: Sidebar no se renderiza para visitantes anónimos.
  const user = useAuthStore((s) => s.user);
  const hasAdmin = useAuthStore((s) => s.hasRole('ADMIN'));
  const hasPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'));
  const hasStock = useAuthStore((s) => s.hasRole('STOCK'));

  // If no authenticated user, render nothing (avoid user.roles access crash)
  if (!user) return null;

  const navItems =
    hasAdmin || hasPedidos || hasStock ? ADMIN_NAV : CLIENT_NAV;

  const handleToggle = () => {
    const next: SidebarMode =
      mode === 'hover'
        ? 'locked-open'
        : mode === 'locked-open'
          ? 'locked-closed'
          : 'hover';
    setMode(next);
    onLockChange?.(next === 'locked-open');
  };

  const handleMouseEnter = () => {
    if (mode === 'hover') setMouseInside(true);
  };

  const handleMouseLeave = () => {
    if (mode === 'hover') setMouseInside(false);
  };

  return (
    <aside
      className={`
        hidden md:flex flex-col
        fixed left-0 top-14 bottom-0
        bg-chrome backdrop-blur-xl border-r border-chrome-border z-20
        overflow-hidden
        transition-all duration-200 ease-out
        ${isExpanded ? 'w-60' : 'w-16'}
      `}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label="Navegación lateral"
    >
      <div className="flex h-12 flex-shrink-0 items-center justify-end px-3 border-b border-chrome-border/50">
        <button
          type="button"
          onClick={handleToggle}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
          title={
            mode === 'hover'
              ? 'Fijar sidebar abierto'
              : mode === 'locked-open'
                ? 'Fijar sidebar cerrado'
                : 'Volver a hover'
          }
          aria-label="Cambiar modo del sidebar"
        >
          {mode === 'locked-open' ? (
            <PanelLeftClose className="h-4 w-4" />
          ) : (
            <PanelLeftOpen className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-2">
        <div className="flex flex-col gap-0.5">
          {navItems.map((item) => (
            <SidebarItem key={item.path} item={item} isExpanded={isExpanded} />
          ))}
        </div>
      </nav>

      <SidebarFooter isExpanded={isExpanded} />
    </aside>
  );
}
