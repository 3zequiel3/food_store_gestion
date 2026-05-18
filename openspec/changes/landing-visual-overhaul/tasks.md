## 0. Pre-apply gates

- [ ] 0.1 ~~Confirmar D2 (hero visual)~~ **DECIDIDO**: CSS shapes animadas (orbes blur). Ver design.md D2.
- [ ] 0.2 ~~Confirmar copy de stats~~ **DECIDIDO**: `+1000 pedidos entregados` / `Entrega en 30 min promedio` / `Productos frescos cada día` / `4.9 ★ valoración`. StatsBar incluida en V1.
- [ ] 0.3 ~~Confirmar InfoSection vs HowItWorks~~ **DECIDIDO**: solo `HowItWorksSection`. `InfoSection` se elimina. Pasos: "Elegí" / "Pagá" / "Recibí". Iconos: `ShoppingBag`, `CreditCard`, `Truck`.
- [ ] 0.4 Verificar que `checkout-pay-first-flow` esté **archivado** (status `complete` y movido a `openspec/changes/archive/`). Si sigue en `in-progress`, parar y avisar al usuario.

## 1. Tokens y keyframes globales

- [ ] 1.1 Agregar keyframes en `frontend/src/index.css` dentro del bloque global de animaciones: `@keyframes fadeInUp` (de `opacity-0 translateY(1rem)` a `opacity-1 translateY(0)`).
- [ ] 1.2 Agregar `@keyframes blob` y `@keyframes float` con transformaciones de scale/translate suaves para los orbes del hero (D2 = CSS shapes, decidido).
- [ ] 1.3 Agregar media query `@media (prefers-reduced-motion: reduce)` que setea `animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; transition-delay: 0ms !important; animation-iteration-count: 1 !important;` sobre `*, *::before, *::after`.
- [ ] 1.4 Verificar visualmente en dev que las animaciones existentes (`animate-pulse`, `animate-spin`, `animate-shimmer`) siguen funcionando.

## 2. Shared hook `useInViewAnimation`

- [ ] 2.1 Crear directorio `frontend/src/pages/landing/hooks/`.
- [ ] 2.2 RED: escribir test `frontend/src/pages/landing/hooks/__tests__/useInViewAnimation.test.tsx` que valide:
  - Retorna `{ ref, isInView }`.
  - `isInView` empieza en `false` y pasa a `true` cuando `IntersectionObserver` dispara el callback con `isIntersecting: true`.
  - Después de `true`, llamadas subsiguientes con `isIntersecting: false` NO vuelven a `false` (once-only).
  - Si `window.matchMedia('(prefers-reduced-motion: reduce)').matches === true`, `isInView` retorna `true` inmediatamente sin esperar al observer.
  - Si `typeof IntersectionObserver === 'undefined'`, `isInView` retorna `true` inmediatamente.
- [ ] 2.3 GREEN: implementar `useInViewAnimation` en `frontend/src/pages/landing/hooks/useInViewAnimation.ts` con la lógica mínima para que los tests pasen.
- [ ] 2.4 REFACTOR: limpiar, validar tipado TS estricto, asegurar cleanup en `useEffect` (`observer.unobserve` + `observer.disconnect`).

## 3. Refactor: extraer secciones a `pages/landing/sections/`

- [ ] 3.1 Crear directorio `frontend/src/pages/landing/sections/`.
- [ ] 3.2 Mover `LandingHeader` (función inline de `LandingPage.tsx`) a `frontend/src/pages/landing/sections/LandingHeader.tsx` como named export. **No reutilizar `TopNavbar`** — la landing tiene su propio header con CTAs de login/registro y branding sin el shell autenticado. Mantener comportamiento idéntico (sin cambios visuales en esta tarea — solo refactor de archivo).
- [ ] 3.3 Mover `HeroSection` original a `frontend/src/pages/landing/sections/HeroSection.tsx`. Mantener visual viejo de momento (cambia en tarea 5).
- [ ] 3.4 Mover `CategoriesSection` original a `frontend/src/pages/landing/sections/CategoriesSection.tsx`. Mantener visual viejo de momento (cambia en tarea 6).
- [ ] 3.5 Mover `FeaturedProductsSection` original a `frontend/src/pages/landing/sections/FeaturedProductsSection.tsx`. Mantener visual viejo de momento (cambia en tarea 7).
- [ ] 3.6 ~~Mover `InfoSection`~~ **DECIDIDO**: `InfoSection` NO se extrae. Eliminar la función `InfoSection` de `LandingPage.tsx` (o del archivo en que resida). No crear `InfoSection.tsx`. `HowItWorksSection` la reemplaza completamente (ver tarea 9).
- [ ] 3.7 Mover `FooterSection` original a `frontend/src/pages/landing/sections/FooterSection.tsx`. Mantener visual viejo (cambia en tarea 9).
- [ ] 3.8 Refactor `frontend/src/pages/LandingPage.tsx` a un composer thin que importa de `./landing/sections/`. Verificar manualmente que `/` sigue renderizando igual que antes del refactor (paridad visual antes de cambios estéticos).
- [ ] 3.9 Ajustar tests existentes de `LandingPage` si los hay (buscar `LandingPage.test.tsx` o similar). Actualizar imports y reasegurarse que pasan.

## 4. Crear `StatsBarSection`

- [ ] 4.1 RED: escribir test `frontend/src/pages/landing/sections/__tests__/StatsBarSection.test.tsx` que valide:
  - Renderiza 3 o 4 items con role `listitem`.
  - El contenedor expone `role="list"`.
  - En viewport `< 640px` los items se renderizan en grid 2x2 (CSS via clase, validable con `getComputedStyle` o test de clase aplicada).
  - El texto de cada stat aparece en pantalla.
  - Si `prefers-reduced-motion: reduce`, la sección es visible sin necesidad de scroll trigger.
- [ ] 4.2 GREEN: crear `frontend/src/pages/landing/sections/StatsBarSection.tsx` con los 4 stats placeholder. Copy exacta del array:
  ```ts
  // TODO(landing-stats): replace with real metrics from analytics/backend when available
  const STATS = [
    { label: "+1000 pedidos entregados" },
    { label: "Entrega en 30 min promedio" },
    { label: "Productos frescos cada día" },
    { label: "4.9 ★ valoración" },
  ];
  ```
  Usar `useInViewAnimation` para fade-in.
- [ ] 4.3 REFACTOR: extraer config inline si conviene; validar accesibilidad (role list / listitem, aria-labels).

## 5. Rediseño visual de `HeroSection`

- [ ] 5.1 RED: escribir test `frontend/src/pages/landing/sections/__tests__/HeroSection.test.tsx` que valide:
  - Renderiza dos áreas distinguibles: copy y visual (data-testid o role-based).
  - En viewport `>= 1024px` el layout es de dos columnas (verificar via clases aplicadas tipo `lg:grid-cols-`).
  - En viewport `< 1024px` colapsa a una columna.
  - NO se renderiza el `Card variant="glass" inline-block` viejo.
  - Las dos CTAs ("Ver menú" e "Ingresar") están presentes y son clickeables.
  - Cuando el usuario está autenticado, "Ver menú" navega a `/cliente/catalogo`; cuando no, a `/login`.
- [ ] 5.2 GREEN: reescribir `HeroSection.tsx` con layout asimétrico 2 columnas (D2 = CSS shapes, decidido):
  - Columna derecha: renderizar 2-3 `<div>` con `bg-primary/20 blur-3xl rounded-full` posicionados absolutamente y animados con `animate-[blob_8s_ease-in-out_infinite]` con `animation-delay` variado.
  - `prefers-reduced-motion: reduce` → orbes visibles pero sin `animation`.
  - Agregar comentario `// TODO(landing-hero-asset): replace CSS orbs with real product photo (AVIF/WebP srcset, loading="eager", fetchpriority="high") when business provides asset.`
- [ ] 5.3 Aplicar `useInViewAnimation` para fade-in del contenido del hero (aunque el hero está siempre en viewport al cargar, mantener consistencia con el resto de la página).
- [ ] 5.4 REFACTOR: extraer componente `HeroVisual` aparte si la lógica del visual (shapes/imagen) crece > 30 líneas.

## 6. Rediseño visual de `CategoriesSection`

- [ ] 6.1 RED: actualizar test existente o crear `frontend/src/pages/landing/sections/__tests__/CategoriesSection.test.tsx` que valide:
  - Renderiza hasta 6 categorías.
  - Cada categoría tiene `role="button"`, `tabIndex={0}` y maneja Enter/Space (KEEP del comportamiento actual).
  - Las cards son visualmente más grandes que la versión original (verificar clase aplicada tipo `h-32` o `min-h-32`).
  - En viewport `< 768px`, el contenedor es scrollable horizontal con snap (verificar clases `overflow-x-auto snap-x`).
  - En viewport `>= 1024px`, el layout es grid de 6 columnas.
  - Estados de loading e error siguen funcionando (skeleton + retry).
- [ ] 6.2 GREEN: rediseñar las cards de categorías — más grandes, mejor jerarquía, icono más prominente, posiblemente con background gradient sutil. Mobile carousel horizontal con `overflow-x-auto snap-x snap-mandatory`.
- [ ] 6.3 Aplicar stagger (`style={{ animationDelay: '${index * 80}ms' }}`) y `useInViewAnimation` para fade-in de la sección.
- [ ] 6.4 REFACTOR: extraer `CategoryCard` si la cantidad de JSX justifica un componente aparte.

## 7. Rediseño visual de `FeaturedProductsSection`

- [ ] 7.1 RED: actualizar test que valide:
  - Renderiza hasta 8 productos.
  - Cada producto usa `LandingProductCard`.
  - Stagger de aparición vía clases CSS (verificar `style.animationDelay` o similar en cada item).
  - Estados loading / error / empty siguen funcionando.
- [ ] 7.2 GREEN: aplicar `useInViewAnimation` para fade-in de la sección. Stagger en items del grid.
- [ ] 7.3 Ajustar paddings y max-width según D9 (`py-24`, `max-w-7xl`). Asegurar diferenciación visual de `CategoriesSection`.

## 8. Rediseño `LandingProductCard` (badges + overlay)

- [ ] 8.1 RED: escribir test `frontend/src/features/products/components/__tests__/LandingProductCard.test.tsx` (extender si ya existe) que valide:
  - Si `producto.destacado === true`, se renderiza un badge "Destacado" con `aria-label="Producto destacado"`.
  - Si el campo `destacado` no existe o es `false`, NO se renderiza el badge.
  - Si `producto.disponible === false`, se renderiza un badge "Sin stock" con `aria-label="Sin stock"`.
  - Si `producto.created_at` existe Y es < 14 días, se renderiza un badge "Nuevo".
  - El componente acepta el mismo prop público `producto: ProductoRead` que antes (backward compat).
  - El componente NO importa `useCartStore` (KEEP del invariante existente).
  - Bajo `prefers-reduced-motion: reduce`, el hover NO aplica scale o translate transforms.
- [ ] 8.2 GREEN: implementar badges con guards defensivos (`if (producto.destacado)`, `if (producto.disponible === false)`, etc.). Posicionar badges absolutamente sobre la imagen, esquina superior izquierda.
- [ ] 8.3 GREEN: implementar overlay sobre imagen al hover: `group-hover:opacity-100` con `bg-gradient-to-t from-background/80 to-transparent`. Image zoom: `group-hover:scale-105 transition-transform duration-500`. Card lift: `hover:-translate-y-1 hover:shadow-xl`. Marcar la card con `class="group"` para que los hijos respondan a hover del padre.
- [ ] 8.4 REFACTOR: si el JSX del card supera ~80 líneas, extraer subcomponentes (`ProductBadges`, `ProductImageWithOverlay`).

## 9. Crear `HowItWorksSection` (reemplaza o convive con `InfoSection`)

- [ ] 9.1 RED: escribir test `frontend/src/pages/landing/sections/__tests__/HowItWorksSection.test.tsx` que valide:
  - Renderiza exactamente 3 cards con números 1, 2, 3.
  - Cada card tiene icono, título y descripción.
  - La lista de pasos usa elemento semántico `<ol>` o equivalente con role list ordenado.
  - En viewport `>= 768px` los pasos están en una fila.
  - En viewport `< 768px` los pasos colapsan vertical.
  - Stagger en la aparición de los 3 pasos.
- [ ] 9.2 GREEN: crear `frontend/src/pages/landing/sections/HowItWorksSection.tsx` con los 3 pasos confirmados:
  - Paso 1: "Elegí" — icono `ShoppingBag` (lucide-react) — descripción breve de 1 línea.
  - Paso 2: "Pagá" — icono `CreditCard` (lucide-react) — descripción breve de 1 línea.
  - Paso 3: "Recibí" — icono `Truck` (lucide-react) — descripción breve de 1 línea.
  - Cards con números grandes (`text-5xl font-bold text-primary`) en la esquina superior.
  - Conectar pasos visualmente con una flecha sutil entre cards en desktop (puede ser un `ChevronRight` decorativo absolutamente posicionado).
- [ ] 9.3 **DECIDIDO (reemplazar)**: asegurarse de que `InfoSection` esté eliminada de `LandingPage.tsx` y del codebase (ver tarea 3.6). El composer de tarea 11 NO incluye `<InfoSection />`. Solo `<HowItWorksSection />`.
- [ ] 9.4 REFACTOR: extraer `StepCard` si conviene.

## 10. Footer rediseñado con 4 secciones

- [ ] 10.1 RED: escribir test `frontend/src/pages/landing/sections/__tests__/FooterSection.test.tsx` que valide:
  - En viewport `>= 1024px`, renderiza 4 columnas (`<nav>` x 4) con sus `aria-label` (Compañía, Ayuda, Contacto, Redes).
  - En viewport `< 1024px` y `>= 640px`, colapsa a 2x2.
  - En viewport `< 640px`, columnas apiladas verticalmente.
  - Copyright se renderiza debajo de las columnas.
  - Cada `<nav>` tiene `aria-label` no vacío.
  - Si el usuario NO está autenticado, los CTAs de auth (Ingresar / Registrarse) están presentes en la columna correspondiente.
- [ ] 10.2 GREEN: reescribir `FooterSection.tsx` con grid responsive y 4 columnas. Copy por columna (placeholder, confirmar con el usuario en revisión final):
  - **Compañía**: Sobre nosotros (TODO link), Trabajá con nosotros (TODO link).
  - **Ayuda**: Preguntas frecuentes (TODO link), Contacto (#contacto).
  - **Contacto**: email genérico (info@foodstore.local — placeholder), teléfono placeholder.
  - **Redes**: Instagram / Facebook / X (iconos lucide, links `#` placeholder).
- [ ] 10.3 Marcar todos los placeholder links con comentario `// TODO(landing-footer): real links provided by client`.

## 11. Composer `LandingPage.tsx`

- [ ] 11.1 Refactor final de `frontend/src/pages/LandingPage.tsx` para que sea un composer thin (~30 líneas):
  ```tsx
  <div className="min-h-screen bg-background">
    <LandingHeader />
    <main>
      <HeroSection />
      <StatsBarSection />
      <CategoriesSection />
      <FeaturedProductsSection />
      <HowItWorksSection />
    </main>
    <FooterSection />
  </div>
  ```
- [ ] 11.2 Verificar paridad funcional manual en `/` (auth y no-auth). El comportamiento de navegación de CTAs no cambia respecto del archivado.

## 12. Tests de accesibilidad y reduced-motion

- [ ] 12.1 Escribir test `frontend/src/pages/__tests__/LandingPage.a11y.test.tsx` usando `vitest-axe` (si está en el proyecto; si no, usar `axe-core` con jsdom) que ejecute axe sobre `<LandingPage />` y falle si hay violaciones de WCAG AA.
- [ ] 12.2 Escribir test `frontend/src/pages/__tests__/LandingPage.reducedMotion.test.tsx` que mockea `window.matchMedia('(prefers-reduced-motion: reduce)')` para retornar `matches: true`, renderiza `<LandingPage />`, y verifica:
  - Las secciones son visibles inmediatamente (no esperan IntersectionObserver).
  - El hover sobre `LandingProductCard` no aplica clases de transform.
- [ ] 12.3 Si `IntersectionObserver` es undefined (mock), las secciones siguen visibles inmediatamente. Test explícito.

## 13. Visual QA y verificación final

- [ ] 13.1 Correr `pnpm dev` y navegar `/` en desktop (1280px+), tablet (768-1024), mobile (375px). Verificar:
  - Hero asimétrico se ve bien en las 3 medidas.
  - Stats bar legible en todas.
  - Categories scroll horizontal en mobile funciona con touch y teclado.
  - Featured products grid no rompe.
  - How It Works steps en fila desktop, stack mobile.
  - Footer 4 cols / 2x2 / stack.
- [ ] 13.2 Verificar con DevTools que toggling `prefers-reduced-motion: reduce` en emulation rendiriza la página sin animaciones y todo el contenido es visible inmediatamente.
- [ ] 13.3 Lighthouse audit local en `/`: LCP ≤ 2.5s, CLS ≤ 0.1, a11y score ≥ 95.
- [ ] 13.4 Test runner full: `pnpm test` debe pasar todos los tests (existentes + nuevos).
- [ ] 13.5 `pnpm lint` y `pnpm typecheck` pasan sin errores.

## 14. Cierre y handoff

- [ ] 14.1 Hacer una pasada manual al diff del change (`git diff devel...HEAD` o similar) para verificar que no se tocó nada fuera del scope (sin tocar `features/checkout/**`, `pages/client/CheckoutPage*`, `features/payments/**`).
- [ ] 14.2 Marcar todos los TODOs introducidos (`TODO(landing-stats)`, `TODO(landing-hero-asset)` si D2 fue C, `TODO(landing-footer)`) en un comentario summary del PR para que queden visibles al revisor.
- [ ] 14.3 Verificar que `LandingProductCard` API pública sigue siendo `{ producto: ProductoRead }` y no se rompió ningún consumer externo.
- [ ] 14.4 Mostrar resultado al usuario para revisión humana ANTES de `/opsx:archive`.

## Estimación

- **Budget total**: 4-6 horas.
- **Mayor riesgo de overrun**: tareas 5 (hero), 8 (badges + overlay del card) y 12 (a11y + reduced-motion tests). Si una de estas se complica, parar y consultar antes de seguir.
