import { ShoppingCart, LogOut, User } from 'lucide-react';
import { useAuthStore } from '../../features/auth/stores/authStore';
import { useCartStore } from '../../features/cart/stores/cartStore';
import { useLogout } from '../../features/auth/hooks/useLogout';

interface TopNavbarProps {
  onCartOpen: () => void;
}

export function TopNavbar({ onCartOpen }: TopNavbarProps) {
  const user = useAuthStore((s) => s.user);
  const hasAdmin = useAuthStore((s) => s.hasRole('ADMIN'));
  const hasPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'));
  const hasStock = useAuthStore((s) => s.hasRole('STOCK'));
  const totalItems = useCartStore((s) =>
    s.items.reduce((sum, item) => sum + item.cantidad, 0),
  );
  const { mutate: logout } = useLogout();

  const isAdmin = hasAdmin || hasPedidos || hasStock;

  return (
    <header
      className="fixed top-0 left-0 right-0 z-30 h-14 bg-chrome backdrop-blur-xl border-b border-chrome-border"
      aria-label="Barra de navegación"
    >
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-primary tracking-tight">
            Food Store
          </span>
        </div>

        <div className="flex items-center gap-2">
          {!isAdmin && (
            <button
              type="button"
              onClick={onCartOpen}
              className="relative flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-glass-hover hover:text-primary transition-all duration-150"
              aria-label={`Carrito${totalItems > 0 ? ` (${totalItems} items)` : ''}`}
            >
              <ShoppingCart className="h-5 w-5" />
              {totalItems > 0 && (
                <span
                  className="absolute -right-0.5 -top-0.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground shadow-sm shadow-primary/30"
                  aria-hidden="true"
                >
                  {totalItems > 9 ? '9+' : totalItems}
                </span>
              )}
            </button>
          )}

          <div className="flex items-center gap-1.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary text-primary-foreground shadow-sm">
              <User className="h-4 w-4" />
            </div>
            {user && (
              <span className="hidden sm:block text-sm text-foreground/90 max-w-[120px] truncate">
                {user.nombre}
              </span>
            )}
            <button
              type="button"
              onClick={() => logout()}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-glass-hover hover:text-destructive transition-all duration-150"
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
