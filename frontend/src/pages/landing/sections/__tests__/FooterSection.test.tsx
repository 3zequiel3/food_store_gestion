import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { FooterSection } from '../FooterSection';
import * as authStoreMod from '../../../../features/auth/stores/authStore';

// ---- Mocks -------------------------------------------------------------------
function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

vi.mock('../../../../features/auth/stores/authStore');

function renderFooter() {
  return render(
    <MemoryRouter>
      <FooterSection />
    </MemoryRouter>,
  );
}

describe('FooterSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    // Default: unauthenticated
    vi.spyOn(authStoreMod, 'useAuthStore').mockImplementation(
      (selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
        selector({ isAuthenticated: () => false }),
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders 4 nav elements with aria-label', () => {
    renderFooter();
    const navs = screen.getAllByRole('navigation');
    expect(navs.length).toBe(4);
    navs.forEach((nav) => {
      expect(nav).toHaveAttribute('aria-label');
      expect(nav.getAttribute('aria-label')).not.toBe('');
    });
  });

  it('renders nav sections: Compañía, Ayuda, Contacto, Redes', () => {
    renderFooter();
    expect(screen.getByRole('navigation', { name: 'Compañía' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Ayuda' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Contacto' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Redes' })).toBeInTheDocument();
  });

  it('renders copyright text below columns', () => {
    renderFooter();
    expect(screen.getByText(/todos los derechos reservados/i)).toBeInTheDocument();
  });

  it('renders auth CTAs (Ingresar/Registrarse) when user is not authenticated', () => {
    renderFooter();
    expect(screen.getByText(/ingresar/i)).toBeInTheDocument();
    expect(screen.getByText(/registrarse/i)).toBeInTheDocument();
  });

  it('does NOT render auth CTAs when user is authenticated', () => {
    vi.spyOn(authStoreMod, 'useAuthStore').mockImplementation(
      (selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
        selector({ isAuthenticated: () => true }),
    );
    renderFooter();
    // No Ingresar/Registrarse buttons in footer
    expect(screen.queryByText(/ingresar/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/registrarse/i)).not.toBeInTheDocument();
  });
});
