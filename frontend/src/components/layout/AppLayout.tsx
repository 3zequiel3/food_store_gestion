import { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { TopNavbar } from './TopNavbar';
import { Sidebar } from './Sidebar';
import { BottomNav } from './BottomNav';
import { CartDrawer } from './CartDrawer';
import { MobileMoreDrawer } from './MobileMoreDrawer';

/**
 * D3 — AppLayout: orquestador del layout dual.
 *
 * Compone:
 *   - TopNavbar: fixed top, siempre visible
 *   - Sidebar: solo desktop (md+), hover-expand + lock
 *   - BottomNav: solo mobile (<md)
 *   - CartDrawer: sheet lateral, reusable mobile/desktop
 *   - MobileMoreDrawer: sheet bottom-up para items admin secundarios
 *   - <Outlet />: contenido de la ruta activa
 *
 * D3 — Layout grid:
 *   main: pt-14 (offset TopNavbar) + md:pl-16 (offset Sidebar collapsed)
 *   Cuando sidebar locked-open: md:pl-60
 *   Mobile: además pb-16 (offset BottomNav)
 *
 * 7.C.3 — CartDrawer y MobileMoreDrawer se cierran en cada route change.
 */
export function AppLayout() {
  const [cartOpen, setCartOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [sidebarLockedOpen, setSidebarLockedOpen] = useState(false);
  const location = useLocation();

  // 7.C.3 — Cerrar drawers al navegar.
  // Pattern: sincronizar UI (drawers) con el sistema externo (router).
  // setState en el body del effect es el patrón correcto acá — equivale a
  // suscribir popstate y setear estado en la callback.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setCartOpen(false);
    setMoreOpen(false);
  }, [location.pathname]);
  /* eslint-enable react-hooks/set-state-in-effect */

  return (
    <div className="min-h-screen bg-background">
      {/* TopNavbar — fixed top, z-30, visible siempre */}
      <TopNavbar onCartOpen={() => setCartOpen(true)} />

      {/* Sidebar — fixed left, solo desktop md+ */}
      <Sidebar onLockChange={setSidebarLockedOpen} />

      {/* Main content */}
      <main
        className={`
          transition-all duration-150 ease-out
          pt-14
          pb-16 md:pb-0
          ${sidebarLockedOpen ? 'md:pl-60' : 'md:pl-16'}
        `}
      >
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <BottomNav onMoreOpen={() => setMoreOpen(true)} />

      {/* Drawers */}
      <CartDrawer isOpen={cartOpen} onClose={() => setCartOpen(false)} />
      <MobileMoreDrawer isOpen={moreOpen} onClose={() => setMoreOpen(false)} />
    </div>
  );
}
