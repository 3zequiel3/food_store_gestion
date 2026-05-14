import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SidebarFooter } from '../../../components/layout/SidebarFooter';
import { useAuthStore } from '../../../features/auth/stores/authStore';
import type { Usuario } from '../../../features/auth/types/auth.types';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  Link: ({ to, children, className, title }: any) => (
    <a href={to} className={className} title={title} data-testid="profile-link">
      {children}
    </a>
  ),
}));

const mockUser: Usuario = {
  id: 1,
  email: 'juan@test.com',
  nombre: 'Juan',
  apellido: 'Perez',
  roles: ['CLIENT'],
};

const mockAdminUser: Usuario = {
  id: 2,
  email: 'admin@test.com',
  nombre: 'Admin',
  apellido: 'User',
  roles: ['ADMIN'],
};

const mockLogout = vi.fn();
vi.mock('../../../features/auth/hooks/useLogout', () => ({
  useLogout: () => ({ mutate: mockLogout }),
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().clearSession();
});

describe('SidebarFooter', () => {
  it('renders null when no user is authenticated', () => {
    const { container } = renderWithClient(<SidebarFooter isExpanded />);
    expect(container.firstChild).toBeNull();
  });

  it('renders user initials as avatar', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded />);
    expect(screen.getByText('JP')).toBeInTheDocument();
  });

  it('renders user name when expanded', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded />);
    expect(screen.getByText('Juan')).toBeInTheDocument();
  });

  it('hides user name when collapsed', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded={false} />);
    expect(screen.queryByText('Juan')).not.toBeInTheDocument();
    expect(screen.getByText('JP')).toBeInTheDocument();
  });

  it('navigates to /cliente/perfil for CLIENT role', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded />);
    const link = screen.getByTestId('profile-link');
    expect(link.getAttribute('href')).toBe('/cliente/perfil');
  });

  it('navigates to /admin/usuarios for ADMIN role', () => {
    useAuthStore.getState().setSession({ user: mockAdminUser });
    renderWithClient(<SidebarFooter isExpanded />);
    const link = screen.getByTestId('profile-link');
    expect(link.getAttribute('href')).toBe('/admin/usuarios');
  });

  it('calls logout when logout button is clicked', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded />);
    const logoutBtn = screen.getByLabelText('Cerrar sesión');
    fireEvent.click(logoutBtn);
    expect(mockLogout).toHaveBeenCalled();
  });

  it('shows logout text when expanded', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded />);
    expect(screen.getByText('Cerrar sesión')).toBeInTheDocument();
  });

  it('hides logout text when collapsed', () => {
    useAuthStore.getState().setSession({ user: mockUser });
    renderWithClient(<SidebarFooter isExpanded={false} />);
    expect(screen.queryByText('Cerrar sesión')).not.toBeInTheDocument();
  });
});
