/**
 * Tests — CreateUserForm component.
 *
 * Verifica:
 * - Renderiza el formulario con todos los campos
 * - Selector de roles muestra: Admin, Cliente, Cocinero
 * - Submit envía POST /api/v1/admin/usuarios con payload correcto
 * - Muestra errores de validación para campos vacíos
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CreateUserForm } from '../components/CreateUserForm';
import * as useCreateUserModule from '../hooks/useCreateUser';

// Mock useCreateUser hook
const mockMutate = vi.fn();

vi.mock('../hooks/useCreateUser', () => ({
  useCreateUser: vi.fn((onSuccess?: () => void) => ({
    mutate: mockMutate,
    isPending: false,
    error: null,
    onSuccess,
  })),
}));

const mockUseCreateUser = vi.mocked(useCreateUserModule.useCreateUser);

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderForm(onClose: () => void = vi.fn()) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <CreateUserForm onClose={onClose} />
    </QueryClientProvider>,
  );
}

// Helper to get inputs by placeholder or id
function getEmailInput(): HTMLInputElement {
  return screen.getByPlaceholderText('usuario@email.com');
}

function getPasswordInput(): HTMLInputElement {
  return screen.getByPlaceholderText('Mínimo 8 caracteres');
}

function getNombreInput(): HTMLInputElement {
  return document.querySelector('#nombre') as HTMLInputElement;
}

function getApellidoInput(): HTMLInputElement {
  return document.querySelector('#apellido') as HTMLInputElement;
}

function getTelefonoInput(): HTMLInputElement {
  return screen.getByPlaceholderText('Opcional');
}

describe('CreateUserForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCreateUser.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      error: null,
    });
  });

  describe('form rendering', () => {
    it('renders the form title as a heading', () => {
      renderForm();
      expect(screen.getByRole('heading', { name: 'Crear usuario' })).toBeInTheDocument();
    });

    it('renders email input', () => {
      renderForm();
      expect(getEmailInput()).toBeInTheDocument();
    });

    it('renders password input', () => {
      renderForm();
      expect(getPasswordInput()).toBeInTheDocument();
    });

    it('renders nombre input', () => {
      renderForm();
      expect(getNombreInput()).toBeInTheDocument();
    });

    it('renders apellido input', () => {
      renderForm();
      expect(getApellidoInput()).toBeInTheDocument();
    });

    it('renders teléfono input', () => {
      renderForm();
      expect(getTelefonoInput()).toBeInTheDocument();
    });

    it('renders the Roles section label', () => {
      renderForm();
      expect(screen.getByText('Roles')).toBeInTheDocument();
    });
  });

  describe('role selector', () => {
    it('shows 3 role buttons: Admin, Cliente, Cocinero', () => {
      renderForm();
      expect(screen.getByRole('button', { name: 'Admin' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cliente' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cocinero' })).toBeInTheDocument();
    });

    it('selects a role when clicked', () => {
      renderForm();
      const adminButton = screen.getByRole('button', { name: 'Admin' });

      // Initially not selected (doesn't have bg-primary class)
      expect(adminButton.className).not.toContain('bg-primary');

      fireEvent.click(adminButton);

      // After click, should be selected
      expect(adminButton.className).toContain('bg-primary');
    });

    it('toggles role off when clicked again', () => {
      renderForm();
      const adminButton = screen.getByRole('button', { name: 'Admin' });

      fireEvent.click(adminButton);
      expect(adminButton.className).toContain('bg-primary');

      fireEvent.click(adminButton);
      expect(adminButton.className).not.toContain('bg-primary');
    });
  });

  describe('validation errors', () => {
    it('shows email validation error when onBlur with invalid value', async () => {
      renderForm();
      const emailInput = getEmailInput();

      fireEvent.change(emailInput, { target: { value: 'not-an-email' } });
      fireEvent.blur(emailInput);

      await waitFor(() => {
        expect(screen.getByText('Email inválido')).toBeInTheDocument();
      });
    });

    it('shows password validation error when onBlur with short password', async () => {
      renderForm();
      const passwordInput = getPasswordInput();

      fireEvent.change(passwordInput, { target: { value: 'short' } });
      fireEvent.blur(passwordInput);

      await waitFor(() => {
        expect(screen.getByText('Mínimo 8 caracteres')).toBeInTheDocument();
      });
    });

    it('shows nombre validation error when onBlur with short value', async () => {
      renderForm();
      const nombreInput = getNombreInput();

      fireEvent.change(nombreInput, { target: { value: 'A' } });
      fireEvent.blur(nombreInput);

      await waitFor(() => {
        expect(screen.getByText('Mínimo 2 caracteres')).toBeInTheDocument();
      });
    });

    it('shows apellido validation error when onBlur with short value', async () => {
      renderForm();
      const apellidoInput = getApellidoInput();

      fireEvent.change(apellidoInput, { target: { value: 'B' } });
      fireEvent.blur(apellidoInput);

      await waitFor(() => {
        expect(screen.getByText('Mínimo 2 caracteres')).toBeInTheDocument();
      });
    });
  });

  describe('form submission', () => {
    function fillValidForm() {
      fireEvent.change(getEmailInput(), {
        target: { value: 'test@example.com' },
      });
      fireEvent.change(getPasswordInput(), {
        target: { value: 'password123' },
      });
      fireEvent.change(getNombreInput(), {
        target: { value: 'Juan' },
      });
      fireEvent.change(getApellidoInput(), {
        target: { value: 'Perez' },
      });
    }

    it('calls mutate with correct payload on valid submit', async () => {
      renderForm();
      fillValidForm();

      // Select a role
      fireEvent.click(screen.getByRole('button', { name: 'Admin' }));

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          nombre: 'Juan',
          apellido: 'Perez',
          telefono: null,
          roles: ['ADMIN'],
        });
      });
    });

    it('includes telefono when provided', async () => {
      renderForm();
      fillValidForm();

      fireEvent.change(getTelefonoInput(), {
        target: { value: '+5491112345678' },
      });
      fireEvent.click(screen.getByRole('button', { name: 'Cocinero' }));

      fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({
            telefono: '+5491112345678',
            roles: ['COCINA'],
          }),
        );
      });
    });

    it('allows multiple role selection', async () => {
      renderForm();
      fillValidForm();

      // Select two roles
      fireEvent.click(screen.getByRole('button', { name: 'Admin' }));
      fireEvent.click(screen.getByRole('button', { name: 'Cocinero' }));

      fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }));

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({
            roles: expect.arrayContaining(['ADMIN', 'COCINA']),
          }),
        );
      });
    });
  });

  describe('cancel button', () => {
    it('calls onClose when Cancelar is clicked', () => {
      const onClose = vi.fn();
      renderForm(onClose);

      fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('loading state', () => {
    it('disables submit button when isPending is true', () => {
      mockUseCreateUser.mockReturnValue({
        mutate: mockMutate,
        isPending: true,
        error: null,
      });

      renderForm();

      expect(screen.getByRole('button', { name: 'Creando...' })).toBeDisabled();
    });

    it('shows "Creando..." text when pending', () => {
      mockUseCreateUser.mockReturnValue({
        mutate: mockMutate,
        isPending: true,
        error: null,
      });

      renderForm();

      expect(screen.getByRole('button', { name: 'Creando...' })).toBeInTheDocument();
    });
  });
});
