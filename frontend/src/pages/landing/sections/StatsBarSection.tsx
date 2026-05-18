import { useInViewAnimation } from '../hooks/useInViewAnimation';

// TODO(landing-stats): replace with real metrics from analytics/backend when available
const STATS = [
  { id: 'orders', label: '+1000 pedidos entregados' },
  { id: 'delivery', label: 'Entrega en 30 min promedio' },
  { id: 'fresh', label: 'Productos frescos cada día' },
  { id: 'rating', label: '4.9 ★ valoración' },
];

export function StatsBarSection() {
  const { ref, isInView } = useInViewAnimation({ threshold: 0.1 });

  return (
    <section
      ref={ref as React.RefCallback<HTMLElement>}
      className={`py-6 sm:py-8 border-y border-glass-border bg-glass backdrop-blur-xl transition-all duration-700 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ul
          role="list"
          className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6"
        >
          {STATS.map((stat) => (
            <li
              key={stat.id}
              role="listitem"
              className="flex flex-col items-center text-center gap-1 py-2"
            >
              <span className="text-sm sm:text-base font-semibold text-foreground leading-snug">
                {stat.label}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
