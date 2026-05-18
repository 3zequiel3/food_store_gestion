import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { useAuthStore } from '../../../features/auth/stores/authStore';
import { useInViewAnimation } from '../hooks/useInViewAnimation';

// TODO(landing-hero-asset): replace CSS orbs with real product photo
// (AVIF/WebP srcset, loading="eager", fetchpriority="high") when business provides asset.

/** Animated CSS blob orb */
function HeroOrb({
  className,
  style,
}: {
  className: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`absolute rounded-full blur-3xl ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

/** Right-side visual: animated CSS orbs */
function HeroVisual() {
  return (
    <div
      data-testid="hero-visual"
      className="relative w-full h-64 lg:h-full min-h-[320px] flex items-center justify-center"
      aria-hidden="true"
    >
      <HeroOrb
        className="w-64 h-64 bg-primary/25 animate-[blob_8s_ease-in-out_infinite]"
        style={{ top: '10%', left: '15%', animationDelay: '0s' }}
      />
      <HeroOrb
        className="w-48 h-48 bg-primary/15 animate-[blob_10s_ease-in-out_infinite]"
        style={{ top: '40%', right: '10%', animationDelay: '3s' }}
      />
      <HeroOrb
        className="w-56 h-56 bg-primary/20 animate-[float_7s_ease-in-out_infinite]"
        style={{ bottom: '5%', left: '30%', animationDelay: '1.5s' }}
      />
    </div>
  );
}

/** Asymmetric two-column hero (D2 = CSS shapes). */
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
    <section className="relative min-h-[88vh] flex items-center overflow-hidden pt-16 bg-gradient-to-br from-primary/5 via-background to-background">
      {/* Full-bleed background gradient */}
      <div
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent"
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-8 lg:gap-16 items-center">
          {/* Left: copy block */}
          <div
            ref={ref as React.RefCallback<HTMLDivElement>}
            data-testid="hero-copy"
            className={`flex flex-col gap-6 transition-all duration-700 ${
              isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
          >
            <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary w-fit">
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

            <p className="text-xl sm:text-2xl text-muted-foreground leading-relaxed max-w-xl">
              Tu comida favorita, a un clic de distancia. Fres&shy;co, rápido y sin complicaciones.
            </p>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 pt-2">
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

          {/* Right: visual */}
          <HeroVisual />
        </div>
      </div>
    </section>
  );
}
