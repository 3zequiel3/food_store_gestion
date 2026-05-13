import { Outlet } from 'react-router-dom';

/**
 * AdminLayout — composición específica del área admin.
 *
 * El shell global (TopNavbar + Sidebar + BottomNav) lo provee AppLayout.
 * Acá solo se delega el render al <Outlet /> de las rutas hijas
 * declaradas en AppRoute.tsx.
 */
export const AdminLayout = () => {
  return (
    <div className="p-4 md:p-6">
      <Outlet />
    </div>
  );
};
