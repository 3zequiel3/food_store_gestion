import { ShoppingCart, LogOut, User } from 'lucide-react';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { useCartStore } from '../../features/cart/stores/cartStore';
import { useLogout } from '../../features/auth/hooks/useLogout';

interface TopNavbarProps {
  onCartOpen: () => void;
}

/**
 * TopNavbar — fixed top, visible en ambos viewports (desktop + mobile).
 * D3: En desktop convive con el Sidebar (sidebar arranca en top-14).
 *
 * Role-aware:
 *   Cliente → cart icon con badge + user menu
 *   Admin/STOCK/PEDIDOS → solo user menu (sin carrito)
 */
export function TopNavbar({ onCartOpen }: TopNavbarProps) {
  const user = useAuthStore((s) => s.user);
  const hasAdmin = useAuthStore((s) => s.hasRole('ADMIN'));
  const hasPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'));
  const hasStock = useAuthStore((s) => s.hasRole('STOCK'));
  const totalItems = useCartStore((s) => s.getTotalItems());
  const { mutate: logout } = useLogout();

  const isAdmin = hasAdmin || hasPedidos || hasStock;

  return (
    <header
      className="fixed top-0 left-0 right-0 z-30 h-14 bg-card border-b border-border"
      aria-label="Barra de navegación"
    >
      <div className="flex h-full items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-primary">Food Store</span>
        </div>

        {/* Right slots */}
        <div className="flex items-center gap-2">
          {/* Cart button — solo para CLIENTE */}
          {!isAdmin && (
            <button
              type="button"
              onClick={onCartOpen}
              className="relative flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              aria-label={`Carrito${totalItems > 0 ? ` (${totalItems} items)` : ''}`}
            >
              <ShoppingCart className="h-5 w-5" />
              {totalItems > 0 && (
                <span
                  className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground"
                  aria-hidden="true"
                >
                  {totalItems > 9 ? '9+' : totalItems}
                </span>
              )}
            </button>
          )}

          {/* User menu — simple avatar + logout */}
          <div className="flex items-center gap-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-primary">
              <User className="h-4 w-4" />
            </div>
            {user && (
              <span className="hidden sm:block text-sm text-foreground max-w-[120px] truncate">
                {user.nombre}
              </span>
            )}
            <button
              type="button"
              onClick={() => logout()}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-destructive transition-colors"
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
