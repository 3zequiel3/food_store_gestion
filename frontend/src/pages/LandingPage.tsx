import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Beef,
  Coffee,
  IceCream,
  Pizza,
  Salad,
  Sandwich,
  ShieldCheck,
  Soup,
  Sparkles,
  Truck,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useProducts } from '../features/products/hooks/useProducts';
import { useCategorias } from '../features/categorias/hooks/useCategorias';
import { LandingProductCard } from '../features/products/components/LandingProductCard';
import { ProductCardSkeleton } from '../features/products/components/ProductCardSkeleton';
import type { CategoriaRead } from '../features/categorias/types/categorias.types';

/** Map category names to lucide icons */
const categoryIconMap: Record<string, React.ElementType> = {
  pizza: Pizza,
  hamburguesa: Beef,
  sandwich: Sandwich,
  cafe: Coffee,
  postre: IceCream,
  ensalada: Salad,
  sopa: Soup,
};

function getCategoryIcon(nombre: string): React.ElementType {
  const key = nombre.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  return categoryIconMap[key] ?? Sparkles;
}

/** Simple inline header for the landing page */
function LandingHeader() {
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

/** Hero section */
function HeroSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  function handleVerMenu() {
    if (isAuthenticated) {
      navigate('/cliente/catalogo');
    } else {
      navigate('/login');
    }
  }

  return (
    <section className="relative min-h-[80vh] flex items-center justify-center overflow-hidden pt-16">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-primary/5" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent" />

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <Card variant="glass" padding="lg" className="inline-block">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-foreground tracking-tight mb-4">
            Food{' '}
            <span className="text-primary">Store</span>
          </h1>
          <p className="text-lg sm:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Tu comida favorita, a un clic de distancia
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={handleVerMenu}
              rightIcon={<ArrowRight className="h-5 w-5" />}
            >
              Ver men&uacute;
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate('/login')}
            >
              Ingresar
            </Button>
          </div>
        </Card>
      </div>
    </section>
  );
}

/** Categories section */
function CategoriesSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  const { data: categorias, isLoading, isError, refetch } = useCategorias();

  function handleCategoryClick() {
    if (isAuthenticated) {
      navigate('/cliente/catalogo');
    } else {
      navigate('/login');
    }
  }

  const displayed = (categorias ?? []).slice(0, 6);

  if (isLoading) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 text-center">
          Explor&aacute; nuestras categor&iacute;as
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-28 rounded-xl bg-glass backdrop-blur-xl border border-glass-border animate-pulse"
            />
          ))}
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-4">
          Explor&aacute; nuestras categor&iacute;as
        </h2>
        <p className="text-muted-foreground mb-4">
          No se pudieron cargar las categor&iacute;as.
        </p>
        <Button variant="outline" onClick={() => refetch()}>
          Reintentar
        </Button>
      </section>
    );
  }

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 text-center">
        Explor&aacute; nuestras categor&iacute;as
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {displayed.map((cat: CategoriaRead) => {
          const Icon = getCategoryIcon(cat.nombre);
          return (
            <Card
              key={cat.id}
              variant="interactive"
              padding="md"
              className="flex flex-col items-center justify-center gap-2 text-center cursor-pointer h-28"
              onClick={handleCategoryClick}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleCategoryClick();
                }
              }}
            >
              <Icon className="h-8 w-8 text-primary" />
              <span className="text-sm font-medium text-foreground line-clamp-1">
                {cat.nombre}
              </span>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

/** Featured Products section */
function FeaturedProductsSection() {
  const { data, isLoading, isError, refetch } = useProducts({
    disponible: true,
    limit: 8,
  });

  const productos = data?.items ?? [];

  if (isLoading) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 text-center">
          Productos destacados
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-4">
          Productos destacados
        </h2>
        <p className="text-muted-foreground mb-4">
          No se pudieron cargar los productos.
        </p>
        <Button variant="outline" onClick={() => refetch()}>
          Reintentar
        </Button>
      </section>
    );
  }

  if (productos.length === 0) {
    return (
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-4">
          Productos destacados
        </h2>
        <p className="text-muted-foreground">
          A&uacute;n no hay productos disponibles.
        </p>
      </section>
    );
  }

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 text-center">
        Productos destacados
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {productos.map((producto) => (
          <LandingProductCard key={producto.id} producto={producto} />
        ))}
      </div>
    </section>
  );
}

/** Info section */
function InfoSection() {
  const infoCards = [
    {
      icon: Truck,
      title: 'Delivery rápido',
      description: 'Recibí tu pedido en la puerta de tu casa en tiempo récord.',
    },
    {
      icon: Sparkles,
      title: 'Productos frescos',
      description: 'Ingredientes seleccionados y preparados con el mayor cuidado.',
    },
    {
      icon: ShieldCheck,
      title: 'Pago seguro',
      description: 'Tus datos están protegidos con encriptación de punta a punta.',
    },
  ];

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-8 text-center">
        &iquest;Por qu&eacute; elegirnos?
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {infoCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.title} variant="glass" padding="lg" className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
                <Icon className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{card.title}</h3>
              <p className="text-sm text-muted-foreground">{card.description}</p>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

/** Footer section */
function FooterSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  return (
    <footer className="border-t border-glass-border bg-glass/50 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-center md:text-left">
            <span className="text-lg font-bold text-primary">Food Store</span>
            <p className="text-sm text-muted-foreground mt-1">
              Tu comida favorita, a un clic de distancia.
            </p>
          </div>

          <nav className="flex items-center gap-4">
            {!isAuthenticated && (
              <>
                <button
                  type="button"
                  onClick={() => navigate('/login')}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Ingresar
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/register')}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Registrarse
                </button>
              </>
            )}
          </nav>
        </div>

        <div className="mt-6 pt-4 border-t border-glass-border text-center">
          <p className="text-xs text-muted-foreground">
            &copy; {new Date().getFullYear()} Food Store. Todos los derechos reservados.
          </p>
        </div>
      </div>
    </footer>
  );
}

/** Main Landing Page */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <LandingHeader />
      <main>
        <HeroSection />
        <CategoriesSection />
        <FeaturedProductsSection />
        <InfoSection />
      </main>
      <FooterSection />
    </div>
  );
}
