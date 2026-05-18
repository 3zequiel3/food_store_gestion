## Context

La capability `public-landing-page` está viva (archivada el 2026-05-18) y satisface el contrato funcional: ruta pública en `/`, secciones presentes, responsive, navegación auth-aware, `LandingProductCard` sin dependencia de `cartStore`. El gap es **visual y de jerarquía**: las cuatro secciones se ven idénticas (mismo `py-16`, mismo `h2 text-2xl`, mismo grid), el hero es un Card centrado sin volumen, no hay motion, no hay social proof, y el footer son dos links.

Este design documenta las decisiones arquitectónicas del rediseño. El contrato de la capability no se modifica — solo se le suman requirements visuales y de motion. El stack frontend ya está fijado (Tailwind v4 con `@theme` OKLCH, React 19, lucide-react). No se agregan dependencias nuevas.

**Stakeholders del visual**:
- Visitante anónimo (público objetivo número 1): necesita entender el negocio y empezar a comprar en <30s.
- Usuario autenticado que vuelve a `/`: necesita un atajo claro al catálogo.
- Equipo de marketing (futuro): los stats y "How It Works" están preparados para ser configurables.

**Constraints**:
- No bundle weight extra (no nuevas libs).
- Mantener LCP ≤ 2.5s (sin assets pesados en el hero por default).
- WCAG AA en color + foco + reduced-motion.
- Compatibilidad con `class="dark"` del theme system (todos los nuevos tokens visuales SOLO via vars CSS existentes).

## Goals / Non-Goals

**Goals**:
- Romper la monotonía de las 4 secciones idénticas con jerarquía visual real (asimetría, anchos distintos, paddings distintos, fondos distintos).
- Agregar motion con CSS-only que se siente premium pero no pesa nada.
- Sumar social proof (stats placeholder) y narrativa de proceso (How It Works) sin requerir backend nuevo.
- Refactor de file structure por sección — `LandingPage.tsx` queda como composer, cada sección es testable aislada.
- Mejorar `LandingProductCard` con badges y overlay sin romper su API pública.
- Respeto explícito de `prefers-reduced-motion: reduce`.

**Non-Goals**:
- Backend nuevo. Stats son placeholders.
- Catálogo navegable público (es `public-catalog-access`).
- SEO / OG / SSR (mismo out-of-scope que el proposal original archivado).
- Internacionalización. UI sigue en español rioplatense que ya tiene el proyecto.
- A/B testing.
- CMS de contenido. "How It Works" pasos y stats son hardcoded en componentes.
- Cambiar tokens OKLCH del theme. Solo se usan los existentes.

## Decisions

### D1 — Motion library: CSS-only + IntersectionObserver

**Decisión**: motion 100% CSS via Tailwind animate utilities + custom keyframes en `index.css`, con un hook `useInViewAnimation` que usa `IntersectionObserver` nativo para trigger de fade-in al entrar viewport. Stagger via `animation-delay` en items de grid.

**Alternativas consideradas**:
- **framer-motion** (~30kb gzip): API ergonómica para variants, stagger orchestration, layout animations, scroll-based reveal. Permite gestos complejos. **Rechazado** porque para esta landing solo necesitamos fade-in, slide-up, hover lift y staggered reveal — todo achievable con CSS sin el costo de 30kb extra.
- **react-spring** (~25kb gzip): físicas reales para microinteracciones. **Rechazado** misma razón: overkill para los efectos requeridos.
- **`@formkit/auto-animate`** (~3kb): liviano, pero solo cubre transiciones de layout (enter/leave), no scroll reveal. **Rechazado** porque la necesidad principal es reveal-on-scroll y staggered grids, no animación de items entrando/saliendo dinámicamente.

**Tradeoffs aceptados**:
- Stagger en grids requiere calcular `animation-delay` por item (`style={{ animationDelay: ${index * 0.1}s }}`) en lugar de orchestration declarativa.
- Sin "layout animations" (FLIP). No las necesitamos.
- Si en el futuro queremos gestures complejos, vamos a tener que agregar la lib y refactorear. Aceptable: cuando llegue, llegará con su propio change.

**Implementación**:
- `useInViewAnimation`: hook que retorna `{ ref, isInView }`. `IntersectionObserver` con `threshold: 0.15`, `rootMargin: '0px'`, `once: true` (no re-trigger).
- Clases utilitarias compuestas: `opacity-0 translate-y-4` base + `opacity-100 translate-y-0 transition-all duration-700` cuando `isInView`.
- Stagger: `style={{ animationDelay: '${index * 80}ms' }}` en items dentro de grids.
- Keyframes adicionales en `index.css` (`@layer base` o como `@theme --animate-*`):
  - `@keyframes fadeInUp`
  - `@keyframes float` (para orbes del hero, si se elige opción C en D2)
  - `@keyframes blob` (para shapes del hero, si C en D2)
- `prefers-reduced-motion`: media query en `index.css` que setea `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important` sobre `*` cuando el usuario lo pide. El hook `useInViewAnimation` también detecta `prefers-reduced-motion` y devuelve `isInView: true` inmediatamente (sin esperar al viewport) para que el contenido no quede invisible.

### D2 — Hero visual: **CSS shapes animadas (orbes blur)**

**Decisión**: CSS gradient orbs / blobs animados. Cero asset externo, cero licensing, look moderno tipo Linear/Stripe/Vercel.

**Implementación**:
- 2-3 `<div>` absolutamente posicionados con `bg-primary/20 blur-3xl rounded-full`, animados con `@keyframes blob` / `@keyframes float` (slow drift, `8s ease-in-out infinite`).
- `animation-delay` variado por orbe para evitar sincronía visual.
- `prefers-reduced-motion: reduce` → orbes visibles pero estáticos (sin `animation`). El contenido copy no se oculta ni depende del orbe.
- Los blobs van detrás del copy con `z-index` menor; el copy se monta sobre un fondo semitransparente (`bg-background/80` o similar) para garantizar contraste WCAG AA.
- LCP impact: nulo. Todo es CSS.

**Upgrade path**: comentario `// TODO(landing-hero-asset): replace CSS orbs with real product photo (AVIF/WebP srcset, loading="eager", fetchpriority="high") when business provides asset.` en `HeroSection.tsx`. No es bloqueante para V1.

**Alternativas descartadas**:
- **Opción A (foto real)**: máximo impacto emocional, pero bloquea la landing hasta que el negocio entregue foto. Un placeholder genérico de stock destroza más la percepción que una landing CSS minimalista bien ejecutada.
- **Opción B (SVG illustration)**: liviano y escalable, pero undraw.co tiene aesthetic genérico identificable. Sin ilustrador propio, no aplica.

**Tradeoffs aceptados**: los CSS shapes no "venden producto" visualmente como una foto real. Se compensa con copy fuerte y tipografía prominente en la columna izquierda.

### D3 — Stats: placeholders con marcado `TODO`

**Decisión**: 4 stats hardcoded en `StatsBarSection.tsx` con comentario `// TODO(landing-stats): replace with real metrics from analytics/backend when available`. Copy confirmada para V1:
- `+1000 pedidos entregados`
- `Entrega en 30 min promedio`
- `Productos frescos cada día`
- `4.9 ★ valoración`

**La sección StatsBar está incluida en V1.** No es opcional en el composer.

**Alternativas consideradas**:
- **Config-driven (JSON/env)**: extracción a un archivo `frontend/src/pages/landing/sections/stats.config.ts` con un array tipado. **Rechazado para V1** porque agrega indirección sin valor real — al ser hardcoded igualmente, mover el array a otro archivo no lo hace "configurable". Cuando exista backend de métricas, se reemplaza con `useQuery` y el archivo de config no era el path correcto.
- **Backend nuevo `/api/v1/metrics/landing`**: out of scope. Sería un change separado.

**Tradeoffs aceptados**:
- Los stats son honestamente aspiracionales hasta que el negocio tenga 1000 pedidos reales. Aceptado para V1: la marca está construyendo aspiración, no mintiendo (categoría "promesa de servicio", no "hecho histórico").
- Copy definitiva marcada con `TODO(landing-stats)` para reemplazo con datos reales.

### D4 — Estructura de secciones (orden y propósito)

**Decisión**: Hero → StatsBar → Categories → FeaturedProducts → HowItWorks → Footer.

**Cada sección con propósito narrativo distinto** (no más loop de "title + grid"):

1. **Hero**: gancho emocional, qué es Food Store, qué hace por vos. CTAs primarias.
2. **StatsBar**: tira horizontal angosta (no full-section), social proof rápido, prueba que somos reales.
3. **Categories**: invitación a explorar. Cards grandes, no minicuadraditos. En mobile, scroll horizontal con snap.
4. **FeaturedProducts**: producto real con precio. Es donde se decide la compra. Card con badges contextuales.
5. **HowItWorks**: para el visitante que entendió qué vendemos pero no cómo funciona — explica el flow ("Elegí" / "Pagá" / "Recibí") en 3 cards numeradas. Iconos lucide-react: `ShoppingBag`, `CreditCard`, `Truck`. **Reemplaza completamente a `InfoSection`** — la función `InfoSection` se elimina del codebase durante apply.
6. **Footer**: cierre profesional. 4 columnas (Compañía / Ayuda / Contacto / Redes) + copyright.

**Sin sección de testimonials en V1** (rechazado): testimonials falsos destruyen confianza más que la suman. Cuando el negocio tenga reviews reales (vía pedidos + rating), se agrega como change separado.

**Anchos y paddings diferenciados** (rompe loop de `py-16 max-w-7xl`):
- Hero: full-bleed, `min-h-[88vh]`, sin `max-w` (el contenido interno sí).
- StatsBar: `py-6 sm:py-8`, `max-w-7xl`, fondo distinto (`bg-glass` con `border-y`) — visualmente es una tira.
- Categories: `py-20`, `max-w-7xl`, fondo gradient sutil.
- FeaturedProducts: `py-24`, `max-w-7xl`, espacio respira más (es el módulo "principal" de la página).
- HowItWorks: `py-20`, `max-w-5xl` (más angosto, foco en el flow narrativo).
- Footer: `py-16`, `max-w-7xl`, fondo `bg-card`/`bg-glass` con `border-t`.

### D5 — Spec delta vs new spec

**Decisión**: delta en `specs/public-landing-page/spec.md` con `## ADDED Requirements`. La capability ya existe (archivada el 2026-05-18). Los requirements existentes (ruta pública, sin redirect, secciones presentes, `LandingProductCard` API, responsive) **siguen siendo verdaderos** después del redesign — solo se les suma comportamiento visual.

**Alternativas consideradas**:
- New capability `landing-visual-design`: **rechazado**. Fragmentar la spec por dimensión visual/funcional rompe el principio de "una capability, un comportamiento testeable extremo a extremo". El test de la landing es uno: `/` renderiza la página correctamente. Visual y funcional viven juntos.
- `MODIFIED Requirements` sobre los existentes: **rechazado**. Los requirements actuales no cambian. Si los marco como MODIFIED, en archive perderíamos detalle. Reglas del CLI: usar ADDED cuando se agrega comportamiento sin alterar el existente.

### D6 — File structure: extracción a `pages/landing/sections/`

**Decisión**: extraer cada sección a su propio archivo bajo `frontend/src/pages/landing/sections/`. `LandingPage.tsx` queda como composer de ~30 líneas que importa y compone las secciones. `LandingHeader` se extrae de su posición inline en `LandingPage.tsx` a `sections/LandingHeader.tsx` — **no se reutiliza `TopNavbar`** porque la landing tiene su propio header con CTAs de login/registro y branding sin el shell autenticado.

**Razones**:
- A 4 secciones está borderline (Single Responsibility ok, monolito legible). A 6-7 secciones (las que tendremos post-redesign) la página se vuelve scroll de 600+ líneas: difícil de leer, difícil de testear, difícil de reordenar.
- Container/Presentational (regla del proyecto): cada sección tiene su responsabilidad propia (Categories fetcha categorías, FeaturedProducts fetcha productos, etc.). Composer arriba, presentational adentro.
- RTL tests por sección aisladamente vs test monolítico de toda la landing.
- Si en el futuro se reordenan secciones o se agrega una nueva (testimonials cuando haya reviews reales), el cambio es composición pura en `LandingPage.tsx`.

**Estructura final**:

```
frontend/src/pages/
├── LandingPage.tsx                    # composer ~30 líneas
└── landing/
    ├── sections/
    │   ├── LandingHeader.tsx
    │   ├── HeroSection.tsx
    │   ├── StatsBarSection.tsx        # nueva
    │   ├── CategoriesSection.tsx
    │   ├── FeaturedProductsSection.tsx
    │   ├── HowItWorksSection.tsx      # reemplaza InfoSection.tsx
    │   └── FooterSection.tsx
    └── hooks/
        └── useInViewAnimation.ts      # shared
```

**Alternativas consideradas**:
- Mantener todo en `LandingPage.tsx` con sub-componentes inline: **rechazado**. A 7 secciones, el archivo supera 500 líneas legibles.
- Crear `frontend/src/features/landing/`: **rechazado**. `landing` no es un dominio (no hay services, ni hooks de fetch propios — usa los de products/categorias). Es una página con secciones. `pages/landing/sections/` lo refleja mejor.

### D7 — `LandingProductCard` evolution

**Decisión**: el componente mantiene su API pública (`producto: ProductoRead`) y suma comportamiento interno:
- Badges contextuales calculados desde `producto`:
  - "Nuevo" si `producto.created_at` es < 14 días (si el campo está disponible en `ProductoRead`; si no, se omite).
  - "Sin stock" si `producto.disponible === false` (la card actual no llega a renderizar productos no disponibles por filtro `disponible: true` en `useProducts`, pero quedamos defensivos).
  - "Destacado" si existe un flag `producto.destacado` (sólo si existe en el schema; si no, se omite — no inventamos campos).
- Overlay sobre imagen al hacer hover: gradient `from-background/80 to-transparent` con CTA prominente y posiblemente "Quick view" como sugerencia visual (sin implementar quick-view real — eso es otro change).
- Image zoom suave en hover (`group-hover:scale-105 transition-transform duration-500`).
- Lift del card en hover (`hover:-translate-y-1 hover:shadow-xl`).

**Tradeoff**: la card hace lookup de campos opcionales con guards (`if (producto.destacado)`). Si el schema `ProductoRead` no expone el campo, el badge simplemente no se renderiza. Esto evita acoplar el redesign visual a cambios de schema backend. Si el backend después agrega flags explícitos, el componente los toma sin refactor.

### D8 — Accesibilidad y reduced-motion (no negociable)

**Decisión**: TODO motion respeta `@media (prefers-reduced-motion: reduce)`. Tres niveles de defensa:
1. Media query global en `index.css` que setea `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; transition-delay: 0ms !important;` sobre `*`.
2. El hook `useInViewAnimation` detecta `prefers-reduced-motion` y retorna `isInView: true` inmediatamente — el contenido aparece directo, sin esperar viewport.
3. Cards con `role="button"` mantienen `tabIndex={0}` y `onKeyDown` para Enter/Space (ya existe en el código actual, KEEP).

**ARIA**:
- Badges con `aria-label` describiendo el estado: "Producto nuevo", "Producto destacado", "Sin stock".
- Stats bar con `role="list"` y items con `role="listitem"`.
- HowItWorks pasos con `<ol>` semántico (lista ordenada).
- Footer con `<nav aria-label="...">` para cada columna.

**Contraste**:
- Texto sobre `bg-glass` (translúcido): mantener `text-foreground` que en light theme es OKLCH 0.15 sobre 0.55 alpha — contraste ratio ok.
- Texto sobre orbes/blobs del hero (si D2 = Opción C): los blobs van con `blur-3xl` muy difuminados detrás del copy. El copy se monta sobre `bg-background` semitransparente para garantizar contraste AA.
- Verificar con axe-core en el test suite.

### D9 — Responsive breakpoints (mantener convención existente)

Usar los breakpoints Tailwind por default que ya usa el proyecto:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

**Layout por sección**:
- **Hero**: 1 columna mobile (copy arriba, visual abajo), 2 columnas `lg:` (copy izquierda 60%, visual derecha 40%).
- **StatsBar**: 2 columnas mobile (grid 2x2), 4 columnas `sm:` (1 fila).
- **Categories**: scroll horizontal con snap mobile (`overflow-x-auto snap-x`), grid 3 columnas `md:`, grid 6 columnas `lg:`. Cards más grandes que el actual (h-32 vs h-28).
- **FeaturedProducts**: 1 col mobile, 2 cols `sm:`, 3 cols `lg:`, 4 cols `xl:` (mantener).
- **HowItWorks**: 1 columna mobile vertical numerada, 3 columnas `md:` con flecha entre cards.
- **Footer**: 1 columna mobile, 2 cols `sm:`, 4 cols `lg:`.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| LCP degrada si en el futuro se reemplaza el hero por foto real (upgrade de D2) | Optimizar con AVIF/WebP, `loading="eager"` + `fetchpriority="high"`, dimensiones explícitas, max 200kb. El `TODO(landing-hero-asset)` guía ese upgrade. Para V1 el hero es CSS puro — LCP nulo. |
| `useInViewAnimation` causa flash de contenido invisible en navegadores sin IntersectionObserver | IntersectionObserver tiene soporte 97% (caniuse). Fallback: si `typeof IntersectionObserver === 'undefined'`, el hook retorna `isInView: true` inmediatamente. Mismo path que `prefers-reduced-motion`. |
| Stagger en grids causa janky en mobile low-end | Usar `transform` + `opacity` exclusivamente (compositor-only). Duración 700ms max. Si el usuario tiene `prefers-reduced-motion: reduce`, se desactiva todo. |
| Tests de motion no son determinísticos | Tests de RTL verifican estado final (post-animation), no transiciones. Para `prefers-reduced-motion`, test específico con `matchMedia` mockeado verificando que el contenido es visible inmediatamente. |
| Badges "Nuevo"/"Destacado" calculan de campos que pueden no existir en `ProductoRead` | Defensive coding: cada badge se renderiza con guard `if (campo)`. Si el campo no existe, el badge se omite — no rompe. |
| Refactor de `LandingPage.tsx` rompe import paths en tests existentes | Verificar tests existentes (`LandingPage.test.tsx` si existe) y actualizar imports. Si los tests testean composición (renderiza Hero + Categories + Products), siguen pasando porque el composer sigue componiendo lo mismo. |
| `checkout-pay-first-flow` en paralelo introduce conflicto en `frontend/src/router/` o `TopNavbar` | Coordinación de timing: este change NO entra a apply hasta que checkout-pay-first-flow esté archivado. Documentado en el proposal. |
| Performance: 6 secciones con IntersectionObserver simultáneo | Cada sección usa su propio observer con `unobserve` después del trigger (`once: true`). Cleanup en useEffect. No hay leak. |
| Copy de stats placeholder se siente "fake" al usuario final | Copy confirmada y marcada con `TODO(landing-stats)`. Los valores son aspiracionales y se reemplazarán con métricas reales en un change futuro. |
| Reduced-motion mal implementado deja contenido invisible para usuarios con la pref activada | Tres niveles de defensa (D8). Test explícito con `matchMedia` mockeado a `prefers-reduced-motion: reduce` que verifica que cards y secciones son visibles inmediatamente. |
| Mobile horizontal scroll en Categories no es accesible con teclado | El scroll horizontal mantiene tabindex; cada card es focusable y enter/space navega. Adicional: agregar dots indicator o flechas opcionales si UX testing lo pide (no V1). |

## Migration Plan

**Despliegue**:
1. Apply del change crea archivos nuevos bajo `pages/landing/sections/` y `pages/landing/hooks/`.
2. `LandingPage.tsx` se refactoriza al composer.
3. `LandingProductCard.tsx` se actualiza con badges + overlay (API pública intacta).
4. `index.css` recibe keyframes nuevos + media query `prefers-reduced-motion`.
5. Tests RTL nuevos por sección + tests existentes de LandingPage se ajustan si rompen.
6. Visual QA manual con storybook-like demo o navegando `/` localmente.
7. Merge a `devel` → preview → merge a `main`.

**Rollback**:
1. Cero impacto backend, DB, o API. Rollback es file-level.
2. Revert del commit en `devel`/`main` restaura `LandingPage.tsx` monolítico + `LandingProductCard.tsx` actual + sin `pages/landing/`.
3. Sin migraciones que revertir.

## Decisiones Cerradas (resumen)

Todas las preguntas abiertas fueron resueltas. No hay preguntas pendientes para `/opsx:apply`.

| # | Pregunta | Decisión |
|---|----------|----------|
| D2 | Hero visual asset | **CSS shapes animadas (orbes blur)** — sin asset externo. `TODO(landing-hero-asset)` para upgrade cuando el negocio entregue foto real. |
| D3 | Copy stats placeholder | **Confirmada**: `+1000 pedidos entregados` / `Entrega en 30 min promedio` / `Productos frescos cada día` / `4.9 ★ valoración`. `TODO(landing-stats)` para reemplazo con datos reales. StatsBar **incluida** en V1. |
| D4 (LandingHeader) | `LandingHeader` reuse vs extracción | **Extraer** a `sections/LandingHeader.tsx`. No reutiliza `TopNavbar` — la landing tiene su propio header con CTAs de auth y branding. |
| D4 (InfoSection) | `InfoSection` vs `HowItWorks` | **Solo `HowItWorks`** — la función `InfoSection` se elimina del codebase durante apply. Pasos: "Elegí" / "Pagá" / "Recibí". Iconos: `ShoppingBag`, `CreditCard`, `Truck` (lucide-react). |
