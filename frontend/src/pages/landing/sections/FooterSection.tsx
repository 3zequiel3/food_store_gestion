import { useNavigate } from 'react-router-dom';
import { Instagram, Facebook, Twitter } from 'lucide-react';
import { useAuthStore } from '../../../features/auth/stores/authStore';

// TODO(landing-footer): real links provided by client

interface FooterColumn {
  label: string;
  ariaLabel: string;
  links: { text: string; href: string }[];
}

const FOOTER_COLUMNS: FooterColumn[] = [
  {
    label: 'Compañía',
    ariaLabel: 'Compañía',
    links: [
      { text: 'Sobre nosotros', href: '#' }, // TODO(landing-footer)
      { text: 'Trabajá con nosotros', href: '#' }, // TODO(landing-footer)
    ],
  },
  {
    label: 'Ayuda',
    ariaLabel: 'Ayuda',
    links: [
      { text: 'Preguntas frecuentes', href: '#' }, // TODO(landing-footer)
      { text: 'Contacto', href: '#contacto' },
    ],
  },
  {
    label: 'Contacto',
    ariaLabel: 'Contacto',
    links: [
      { text: 'info@foodstore.local', href: 'mailto:info@foodstore.local' }, // TODO(landing-footer)
      { text: '+54 11 0000-0000', href: 'tel:+541100000000' }, // TODO(landing-footer)
    ],
  },
];

export function FooterSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  return (
    <footer className="border-t border-glass-border bg-card/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Brand row */}
        <div className="mb-12">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-2xl font-extrabold text-primary tracking-tight"
          >
            Food Store
          </button>
          <p className="text-sm text-muted-foreground mt-1 max-w-xs">
            Tu comida favorita, a un clic de distancia.
          </p>
        </div>

        {/* Columns grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
          {FOOTER_COLUMNS.map((col) => (
            <nav key={col.label} aria-label={col.ariaLabel}>
              <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">
                {col.label}
              </h3>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link.text}>
                    <a
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link.text}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          {/* Social column */}
          <nav aria-label="Redes">
            <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-4">
              Redes
            </h3>
            <div className="flex items-center gap-4">
              <a
                href="#" // TODO(landing-footer)
                aria-label="Instagram"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <Instagram className="h-5 w-5" />
              </a>
              <a
                href="#" // TODO(landing-footer)
                aria-label="Facebook"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <Facebook className="h-5 w-5" />
              </a>
              <a
                href="#" // TODO(landing-footer)
                aria-label="X (Twitter)"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <Twitter className="h-5 w-5" />
              </a>
            </div>

            {!isAuthenticated && (
              <div className="mt-6 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  Ingresar
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/register')}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors text-left"
                >
                  Registrarse
                </button>
              </div>
            )}
          </nav>
        </div>

        {/* Copyright */}
        <div className="pt-6 border-t border-glass-border">
          <p className="text-xs text-muted-foreground text-center">
            &copy; {new Date().getFullYear()} Food Store. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
}
