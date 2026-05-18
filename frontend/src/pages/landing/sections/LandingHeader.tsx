import { useNavigate } from 'react-router-dom';
import { ArrowRight, ShoppingBag } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { useAuthStore } from '../../../features/auth/stores/authStore';

/** Landing-page-specific header with auth CTAs. Does NOT reuse TopNavbar. */
export function LandingHeader() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-glass backdrop-blur-xl border-b border-glass-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-xl font-bold text-primary tracking-tight"
        >
          Food Store
        </button>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/cliente/catalogo')}
            leftIcon={<ShoppingBag className="h-4 w-4" />}
          >
            Shop
          </Button>

          {isAuthenticated ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/dashboard')}
              leftIcon={<ArrowRight className="h-4 w-4" />}
            >
              Ir al panel
            </Button>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/login')}
              >
                Ingresar
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/register')}
              >
                Registrarse
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
