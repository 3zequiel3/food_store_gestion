/**
 * Tests — Group 2: LoginForm post-login redirect
 *
 * 2.1 (RED): LoginForm with state.from navigates to state.from on success.
 * 2.2 (PASS): LoginForm without state.from navigates to '/' on success.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ---- Mock useNavigate to track navigation calls ------------------------------
const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ---- Mock useLogin so we control onSuccess call -----------------------------
type LoginMutate = (
  credentials: { email: string; password: string },
  opts?: { onSuccess?: () => void }
) => void;

let capturedOnSuccess: (() => void) | undefined;

const mockLoginMutate: LoginMutate = (_credentials, opts) => {
  capturedOnSuccess = opts?.onSuccess;
};

vi.mock('../../hooks/useLogin', () => ({
  useLogin: () => ({
    mutate: mockLoginMutate,
    isPending: false,
    error: null,
  }),
}));

// ---- Import component AFTER mocks -------------------------------------------
import { LoginForm } from '../LoginForm';

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

/**
 * Renders LoginForm inside a MemoryRouter at /login with optional location.state.
 */
function renderLoginForm(locationState?: { from?: string }) {
  const qc = makeQueryClient();

  if (locationState !== undefined) {
    return render(
      <QueryClientProvider client={qc}>
        <MemoryRouter
          initialEntries={[{ pathname: '/login', state: locationState }]}
        >
          <Routes>
            <Route path="/login" element={<LoginForm />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function submitLoginForm() {
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'test@example.com' },
  });
  fireEvent.change(screen.getByLabelText(/contraseña/i), {
    target: { value: 'password123' },
  });
  fireEvent.click(screen.getByRole('button', { name: /ingresar/i }));
  // Wait for mutate to be called (tanstack form submit is async)
  await waitFor(() => {
    expect(capturedOnSuccess).toBeDefined();
  });
  // Trigger the captured onSuccess callback to simulate a successful login
  capturedOnSuccess!();
}

describe('LoginForm post-login redirect (Group 2)', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    capturedOnSuccess = undefined;
  });

  // 2.1 — RED: with state.from, navigate to that path with replace: true
  it('2.1 navigates to state.from on successful login when state.from is present', async () => {
    renderLoginForm({ from: '/cliente/checkout' });
    await submitLoginForm();
    expect(mockNavigate).toHaveBeenCalledWith('/cliente/checkout', { replace: true });
  });

  // 2.2 — without state.from, navigate to '/' with replace: true (consistent with D5)
  it('2.2 navigates to / on successful login when state.from is absent', async () => {
    renderLoginForm();
    await submitLoginForm();
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });
});
