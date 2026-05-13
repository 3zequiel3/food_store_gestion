import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Package,
  ClipboardList,
  Users,
  BarChart3,
  FolderTree,
  Carrot,
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

// ─── Nav items definition ─────────────────────────────────────────────────────

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
    label: 'Productos',
    path: '/admin/productos',
    icon: <Package className="h-5 w-5" />,
    subItems: [
      { label: 'Listado', path: '/admin/productos' },
      { label: 'Crear', path: '/admin/productos/nuevo' },
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
  {
    label: 'Categorías',
    path: '/admin/categorias',
    icon: <FolderTree className="h-5 w-5" />,
  },
  {
    label: 'Ingredientes',
    path: '/admin/ingredientes',
    icon: <Carrot className="h-5 w-5" />,
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

// ─── SidebarItem component ────────────────────────────────────────────────────

interface SidebarItemProps {
  item: NavItem;
  isExpanded: boolean;
}

function SidebarItem({ item, isExpanded }: SidebarItemProps) {
  const location = useLocation();
  const isActive = location.pathname.startsWith(item.path);

  // Submenú: autoexpandido si la ruta actual está bajo este item
  const [subMenuOpen, setSubMenuOpen] = useState(isActive);

  const hasSubItems = item.subItems && item.subItems.length > 0;

  // D3: submenús solo en estado expanded
  const showSubMenu = isExpanded && hasSubItems && subMenuOpen;

  const handleClick = () => {
    if (hasSubItems && isExpanded) {
      setSubMenuOpen((prev) => !prev);
    }
  };

  const itemClasses = `
    flex items-center gap-3 rounded-lg px-3 h-10 w-full
    transition-colors duration-100 cursor-pointer
    ${isActive
      ? 'bg-accent text-accent-foreground font-medium'
      : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
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
          {/* Ícono — siempre visible */}
          <span className="flex-shrink-0">{item.icon}</span>

          {/* Label + chevron — solo en expanded */}
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

      {/* Sub-items */}
      {showSubMenu && (
        <div className="ml-8 mt-1 flex flex-col gap-0.5">
          {item.subItems!.map((sub) => (
            <Link
              key={sub.path}
              to={sub.path}
              className={`
                flex h-9 items-center rounded-md px-3 text-sm transition-colors
                ${location.pathname === sub.path
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
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

// ─── Sidebar component ────────────────────────────────────────────────────────

type SidebarMode = 'hover' | 'locked-open' | 'locked-closed';

interface SidebarProps {
  /** Callback para notificar a AppLayout del ancho actual (locked-open vs collapsed) */
  onLockChange?: (isLockedOpen: boolean) => void;
}

/**
 * D3 — Sidebar desktop con hover-expand + lock.
 *
 * Estados:
 *   hover → expand on mouseenter, collapse on mouseleave
 *   locked-open → siempre expandido (240px), ignora hover
 *   locked-closed → siempre colapsado (64px), ignora hover
 *
 * Click en toggle cicla: hover → locked-open → locked-closed → hover
 *
 * Solo visible en md+ (hidden md:flex — en mobile se usa BottomNav).
 */
export function Sidebar({ onLockChange }: SidebarProps) {
  const [mode, setMode] = useState<SidebarMode>('hover');
  const [mouseInside, setMouseInside] = useState(false);

  // isExpanded: true si locked-open o si hover && mouse adentro
  const isExpanded =
    mode === 'locked-open' || (mode === 'hover' && mouseInside);

  // 7.A.8 — Role-aware nav: prioridad ADMIN > PEDIDOS > STOCK > CLIENTE
  const hasAdmin = useAuthStore((s) => s.hasRole('ADMIN'));
  const hasPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'));
  const hasStock = useAuthStore((s) => s.hasRole('STOCK'));

  const navItems =
    hasAdmin || hasPedidos || hasStock ? ADMIN_NAV : CLIENT_NAV;

  const handleToggle = () => {
    setMode((current) => {
      const next: SidebarMode =
        current === 'hover'
          ? 'locked-open'
          : current === 'locked-open'
            ? 'locked-closed'
            : 'hover';
      onLockChange?.(next === 'locked-open');
      return next;
    });
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
        bg-card border-r border-border z-20
        overflow-hidden
        transition-all duration-150 ease-out
        ${isExpanded ? 'w-60' : 'w-16'}
      `}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label="Navegación lateral"
    >
      {/* Toggle button */}
      <div className="flex h-12 flex-shrink-0 items-center justify-end px-3 border-b border-border/50">
        <button
          type="button"
          onClick={handleToggle}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
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

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-2">
        <div className="flex flex-col gap-0.5">
          {navItems.map((item) => (
            <SidebarItem key={item.path} item={item} isExpanded={isExpanded} />
          ))}
        </div>
      </nav>
    </aside>
  );
}
