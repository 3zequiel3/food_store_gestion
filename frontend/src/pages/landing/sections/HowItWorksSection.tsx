import { ShoppingBag, CreditCard, Truck, ChevronRight } from 'lucide-react';
import { useInViewAnimation } from '../hooks/useInViewAnimation';

interface Step {
  number: number;
  icon: React.ElementType;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    number: 1,
    icon: ShoppingBag,
    title: 'Elegí',
    description: 'Explorá nuestro menú y sumá tus platos favoritos al carrito.',
  },
  {
    number: 2,
    icon: CreditCard,
    title: 'Pagá',
    description: 'Completá tu pedido con pago seguro en un solo paso.',
  },
  {
    number: 3,
    icon: Truck,
    title: 'Recibí',
    description: 'Te lo llevamos a tu puerta en tiempo récord.',
  },
];

/** Individual step card */
function StepCard({ step, index }: { step: Step; index: number }) {
  const Icon = step.icon;
  return (
    <li
      style={{ animationDelay: `${index * 80}ms` }}
      className="relative flex flex-col gap-4 rounded-2xl bg-glass backdrop-blur-xl border border-glass-border p-6"
    >
      {/* Step number */}
      <span className="text-5xl font-bold text-primary/20 leading-none select-none" aria-hidden="true">
        {step.number}
      </span>
      <span className="sr-only">{`Paso ${step.number}`}</span>

      {/* Icon */}
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10">
        <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
      </div>

      {/* Text */}
      <div className="flex flex-col gap-1">
        <h3 className="text-xl font-bold text-foreground">{step.title}</h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
      </div>
    </li>
  );
}

export function HowItWorksSection() {
  const { ref, isInView } = useInViewAnimation();

  return (
    <section
      ref={ref as React.RefCallback<HTMLElement>}
      className={`py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-muted/30 to-background transition-all duration-700 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-3">
            ¿Cómo funciona?
          </h2>
          <p className="text-muted-foreground text-lg">
            Tres pasos y tu pedido está en camino.
          </p>
        </div>

        {/* Steps — semantic ol */}
        <div className="relative">
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map((step, index) => (
              <StepCard key={step.number} step={step} index={index} />
            ))}
          </ol>

          {/* Desktop connector arrows */}
          <div className="hidden md:flex absolute top-1/3 left-0 right-0 -translate-y-1/2 justify-around px-4 pointer-events-none" aria-hidden="true">
            <div className="flex items-center gap-2 opacity-20">
              <ChevronRight className="h-6 w-6 text-primary" />
            </div>
            <div className="flex items-center gap-2 opacity-20">
              <ChevronRight className="h-6 w-6 text-primary" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
