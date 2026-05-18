import { useNavigate } from 'react-router-dom';
import {
  Beef,
  Coffee,
  IceCream,
  Pizza,
  Salad,
  Sandwich,
  Sparkles,
  Soup,
} from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';
import { useAuthStore } from '../../../features/auth/stores/authStore';
import { useCategorias } from '../../../features/categorias/hooks/useCategorias';
import { useInViewAnimation } from '../hooks/useInViewAnimation';
import type { CategoriaRead } from '../../../features/categorias/types/categorias.types';

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
  const key = nombre.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  return categoryIconMap[key] ?? Sparkles;
}

/** Individual category card */
function CategoryCard({
  cat,
  icon: Icon,
  index,
  onClick,
}: {
  cat: CategoriaRead;
  icon: React.ElementType;
  index: number;
  onClick: () => void;
}) {
  return (
    <Card
      variant="interactive"
      padding="md"
      className="snap-start flex flex-col items-center justify-center gap-3 text-center cursor-pointer
        min-h-[8rem] lg:min-h-[8rem] hover:-translate-y-1 hover:shadow-lg transition-all duration-300"
      onClick={onClick}
      role="button"
      tabIndex={0}
      style={{ animationDelay: `${index * 80}ms` }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10">
        <Icon className="h-7 w-7 text-primary" />
      </div>
      <span className="text-sm font-semibold text-foreground line-clamp-1">
        {cat.nombre}
      </span>
    </Card>
  );
}

export function CategoriesSection() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  const { data: categorias, isLoading, isError, refetch } = useCategorias();
  const { ref, isInView } = useInViewAnimation();

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
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-background to-muted/30">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-10 text-center">
            Explor&aacute; nuestras categor&iacute;as
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="min-h-[8rem] rounded-xl bg-glass backdrop-blur-xl border border-glass-border animate-pulse"
              />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-background to-muted/30">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Explor&aacute; nuestras categor&iacute;as
          </h2>
          <p className="text-muted-foreground mb-4">
            No se pudieron cargar las categor&iacute;as.
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Reintentar
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section
      ref={ref as React.RefCallback<HTMLElement>}
      className={`py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-background to-muted/30 transition-all duration-700 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-10 text-center">
          Explor&aacute; nuestras categor&iacute;as
        </h2>
        {/* Mobile: horizontal scroll with snap; md+: grid */}
        <div className="flex overflow-x-auto snap-x snap-mandatory gap-4 pb-2 md:pb-0
          md:grid md:grid-cols-3 md:overflow-x-visible lg:grid-cols-6">
          {displayed.map((cat: CategoriaRead, index: number) => (
            <div key={cat.id} className="flex-shrink-0 w-40 md:w-auto snap-start">
              <CategoryCard
                cat={cat}
                icon={getCategoryIcon(cat.nombre)}
                index={index}
                onClick={handleCategoryClick}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
