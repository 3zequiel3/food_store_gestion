## Why

La landing actual (archivada el 2026-05-18 como `public-landing-page`) cumple el contrato funcional — `/` es pública, hay hero + categorías + productos + info + footer — pero visualmente es plana y monótona. El usuario la describió como "re contra fea": cuatro secciones idénticas en estructura (`py-16` + `h2 text-2xl` + grid), un hero anémico (un `Card glass inline-block` centrado con gradient `primary/10` casi invisible), cero motion, sin prueba social, sin asimetría y un footer que es apenas dos links de auth. Es una landing que funciona pero no convierte ni transmite identidad.

Este change es un **rediseño visual completo** de la capability `public-landing-page` sin tocar su contrato funcional (rutas, navegación, integraciones con `useProducts`/`useCategorias`, `LandingProductCard` API). Suma estructura, jerarquía visual, motion respetando `prefers-reduced-motion`, badges en productos, footer real y stats placeholder. Es la primera impresión del negocio: si no transmite cuidado, perdemos al visitante en los primeros 3 segundos.

## What Changes

- **Hero asimétrico**: rompe el patrón "card centrado", usa dos columnas en desktop (copy a la izquierda, visual a la derecha) con stack vertical en mobile. Background con orbes/blobs de gradiente animados con CSS (`@keyframes blob`), sin asset externo. Look reference: Linear, Stripe. `prefers-reduced-motion: reduce` → orbes visibles pero estáticos. Upgrade a foto real marcado con `TODO(landing-hero-asset)` para cuando el negocio entregue asset. Ver decisión D2 en design.md.
- **Stats Bar nueva**: tira horizontal entre Hero y Categories con 3-4 métricas placeholder ("+1000 pedidos", "Entrega en 30 min", "Productos frescos", "4.9 ★"). Mark con `TODO(landing-stats)` para hookear métricas reales en V2.
- **Categories Section rediseñada**: cards más grandes y expresivas (no 6 cuadraditos de 7rem), con espacio para imagen o icono grande, hover con elevación real, posiblemente carousel horizontal en mobile.
- **Featured Products con badges**: `LandingProductCard` suma badges contextuales ("Nuevo", "Destacado", "Sin stock" — con datos disponibles en `ProductoRead`), overlay sobre la imagen al hacer hover, microinteracciones en el botón CTA.
- **How It Works reemplaza Info**: 3 pasos numerados ("Elegí → Pagá → Recibí") con iconos de lucide-react (`ShoppingBag`, `CreditCard`, `Truck`) + descripción breve, conecta el "¿por qué elegirnos?" actual con una narrativa de proceso. La función `InfoSection` se **elimina** de `LandingPage.tsx` durante el apply — no coexisten las dos secciones.
- **Footer real**: 4 secciones (Compañía / Ayuda / Contacto / Redes) en grid responsive, con copyright debajo. Reemplaza el navbar de 2 links actual.
- **Motion design CSS-only**: fade-in + slide-up al entrar en viewport (IntersectionObserver), stagger en grids con `animation-delay`, hover microinteractions (lift, glow, image zoom). Respetar `prefers-reduced-motion: reduce` desactivando todo movimiento.
- **Refactor de archivos**: extraer secciones de `LandingPage.tsx` a `frontend/src/pages/landing/sections/` siguiendo Container/Presentational. `LandingPage.tsx` queda como composer ~30 líneas.

**No hay cambios** en rutas, guards, API calls, ni en el contrato público de `LandingProductCard` (mismas props `producto: ProductoRead`). Las nuevas props son opcionales y backward-compatible.

**Sin nuevas dependencias**: motion 100% CSS + IntersectionObserver. `framer-motion` queda explícitamente rechazado para V1 (justificación en design.md D1).

## Capabilities

### New Capabilities

Ninguna. Este change es un rediseño visual de una capability existente.

### Modified Capabilities

- `public-landing-page`: agrega requirements visuales y de motion sobre los existentes. Los requirements actuales (ruta pública, secciones presentes, responsive, navegación auth-aware) **no se modifican** — siguen vigentes. La delta es **aditiva**: hero asimétrico con dos columnas, stats bar, sección "How It Works", footer con 4 secciones, badges en productos, motion con respeto de `prefers-reduced-motion`, y estructura de archivos por sección. Ver `specs/public-landing-page/spec.md` (deltas `## ADDED Requirements`).

## Impact

- **Frontend (único stack afectado)**:
  - `frontend/src/pages/LandingPage.tsx`: refactor — pasa de monolito de ~400 líneas a composer de ~30 líneas que importa secciones.
  - `frontend/src/pages/landing/sections/` (nuevo directorio):
    - `LandingHeader.tsx` (extraído de `LandingPage.tsx`; header propio con CTAs de login/registro, no reutiliza `TopNavbar`)
    - `HeroSection.tsx`
    - `StatsBarSection.tsx` (nueva)
    - `CategoriesSection.tsx`
    - `FeaturedProductsSection.tsx`
    - `HowItWorksSection.tsx` (reemplaza `InfoSection` — la función `InfoSection` se elimina del codebase)
    - `FooterSection.tsx`
  - `frontend/src/features/products/components/LandingProductCard.tsx`: agrega badges, overlay en hover, mantiene API pública.
  - `frontend/src/pages/landing/hooks/useInViewAnimation.ts` (nuevo): hook compartido para fade-in al entrar viewport vía IntersectionObserver.
  - `frontend/src/index.css`: posibles keyframes adicionales (`@keyframes fadeInUp`, `@keyframes float`) en el bloque global de animaciones. **Sin tocar tokens existentes**.
- **Backend**: cero impacto. No se consumen endpoints nuevos. Los stats son placeholders hardcodeados.
- **APIs**: cero impacto.
- **Tests**: RTL unit tests por sección, tests de accesibilidad (axe), test explícito de `prefers-reduced-motion: reduce`. Tests existentes de `LandingPage` se actualizan (cambia la composición pero el contrato funcional sigue).
- **Dependencias**: **NINGUNA nueva**. CSS-only + IntersectionObserver (Web API nativa).
- **Performance**: las animaciones se ejecutan en `transform`/`opacity` (compositor-only). Imágenes lazy-loaded vía `loading="lazy"` (ya existe en `ProductImage`). LCP no debe degradarse — el hero es texto + CSS, no asset pesado por default.
- **Accesibilidad**:
  - Respeta `prefers-reduced-motion: reduce` (todas las animaciones se desactivan).
  - Mantiene el keyboard nav existente en cards (Enter/Space).
  - Badges con `aria-label` para lectores de pantalla.
  - Contraste WCAG AA con tokens OKLCH ya validados.
- **Riesgos**: ver `design.md` sección "Risks". Las decisiones de diseño D2–D4 están cerradas; no hay preguntas abiertas pendientes.
- **Out of scope** (sigue lo del proposal original archivado):
  - SEO / meta tags / Open Graph.
  - Catálogo público navegable (es `public-catalog-access`).
  - Cambios en `routing-guards` (separado).
  - Cambios en `CheckoutPage` (es `checkout-single-page-ux`).
  - A/B testing, analytics, CMS de contenido.
- - **Bloqueante**: este change **NO debe entrar a `apply` hasta que `checkout-pay-first-flow` esté archivado**. Razón: aunque no compartan archivos, ambos tocan UX del cliente y queremos evitar merges conflictivos en `frontend/src/router/` o en commits de revisión paralelos.
