import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { useAuthStore } from '../../../features/auth/stores/authStore';
import { useInViewAnimation } from '../hooks/useInViewAnimation';

/** Full-bleed background photo with AVIF → WebP → PNG fallback chain. */
function HeroBackground() {
  return (
    <picture data-testid="hero-visual" aria-hidden="true">
      <source srcSet="/hero/hero.avif" type="image/avif" />
      <source srcSet="/hero/hero.webp" type="image/webp" />
      <img
        src="/hero/hero.png"
        alt=""
        loading="eager"
        fetchPriority="high"
        className="absolute inset-0 w-full h-full object-cover"
      />
    </picture>
  );
}

/** Hero with photo background and gradient overlay for legibility. */
export function HeroSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  const { ref, isInView } = useInViewAnimation({ threshold: 0.05 });

  function handleVerMenu() {
    if (isAuthenticated) {
      navigate('/cliente/catalogo');
    } else {
      navigate('/login');
    }
  }

  return (
    <section className="relative min-h-[80vh] lg:min-h-[88vh] flex items-center overflow-hidden pt-16">
      <HeroBackground />

      <div
        className="absolute inset-0 bg-gradient-to-b from-background/85 via-background/70 to-background/85 lg:bg-gradient-to-r lg:from-background/95 lg:via-background/70 lg:to-transparent"
        aria-hidden="true"
      />
      <div
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent"
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          ref={ref as React.RefCallback<HTMLDivElement>}
          data-testid="hero-copy"
          className={`max-w-2xl flex flex-col gap-6 text-center lg:text-left items-center lg:items-start transition-all duration-700 ${
            isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary w-fit backdrop-blur-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
            </span>
            Pedidos en tu zona
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-foreground tracking-tight leading-[1.05]">
            Food{' '}
            <span className="text-primary">Store</span>
          </h1>

          <p className="text-xl sm:text-2xl text-muted-foreground leading-relaxed max-w-xl mx-auto lg:mx-0">
            Tu comida favorita, a un clic de distancia. Fres&shy;co, rápido y sin complicaciones.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3 pt-2">
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
        </div>
      </div>
    </section>
  );
}
