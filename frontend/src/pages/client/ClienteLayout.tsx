import { Outlet } from 'react-router-dom';

/**
 * ClienteLayout — composición específica del área cliente.
 *
 * El shell global (TopNavbar + BottomNav + CartDrawer) lo provee AppLayout.
 * Acá solo se delega el render al <Outlet /> de las rutas hijas
 * declaradas en AppRoute.tsx.
 */
export const ClienteLayout = () => {
  return (
    <div className="p-4 md:p-6">
      <Outlet />
    </div>
  );
};
