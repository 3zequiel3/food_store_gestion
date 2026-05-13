# Roadmap Fase B — Changes pendientes (frontend + backend bridge)

Este documento expande cada change que falta para cerrar el integrador. Cada entrada responde dos preguntas:

- **En qué consiste**: alcance concreto, archivos clave, decisiones técnicas locked.
- **Por qué se necesita**: justificación de producto / negocio / arquitectura.

Las dependencias, historias de usuario y duración estimada viven en `docs/CHANGES.md`. Este archivo es la versión narrativa del roadmap; cuando un change pase a la fase de proposal (`/opsx:propose`), el sub-agent toma de acá la intención y la traduce a artifacts formales.

> **Nota**: los `.txt` de la cátedra (`Integrador.txt`, `Historias_de_usuario.txt`) fueron generados por IA sin revisión humana. No son canónicos. Cuando un alcance contradice el código real del backend o la lectura técnica del equipo, gana el código + esta narrativa.

---

## 0. `catalog-filters-and-leaf-categories-backend` — pre-bloqueante de Sprint 7

**Estado**: implementado, en working tree, pendiente de commit + archive.

### En qué consiste

Extensión del backend de productos y categorías para soportar la UX de catálogo que viene en Sprint 7. Sin schema migration — todo se resuelve con consultas y validaciones.

Lo que agrega:

- **Filtro recursivo por categoría**: `GET /productos?categoria_id=X` ahora matchea productos de `X` y de todas sus descendientes activas (CTE recursivo en `ProductRepository`, sigue el patrón de `CategoryRepository.get_tree_cte()` que ya estaba probado en SQLite).
- **Filtro de alérgenos granular**: nuevo param `excluir_alergeno_ids: list[int]`. Excluye productos cuyos ingredientes tengan ID en la lista *y* `es_removible=False` para ese producto. El booleano viejo `excluir_alergenos=true` se mantiene como shortcut backward-compat.
- **Validación leaf-only en asignación de categorías**: `POST /productos` y `PUT /productos/{id}/categorias` rechazan con 422 si alguna `categoria_id` tiene hijas activas. Mensaje accionable: nombre de la categoría intermedia + nombres de las hijas que el admin tiene que elegir en su lugar.
- **Auto-`disponible=false` cuando un producto queda sin categoría hoja válida**: hook post-mutación en `ProductService`. El admin reactiva manualmente con `PATCH /disponibilidad` después de reasignar. No hay reactivación automática (auditabilidad).
- **Filtro `sin_categoria=true`** en `GET /productos`: lista productos con cero categorías activas. Pensado para una vista admin "sin categorizar".
- **Block-on-promote guard**: `CategoryService.create()` rechaza crear una hija si el padre tiene productos asignados activos. Forza al admin a reasignar antes de subcategorizar.
- **`GET /categorias?solo_hojas=true`**: lista plana (no árbol) de categorías sin hijas activas. Es el endpoint que el admin frontend va a usar para poblar el `<select>` de "asignar categoría". Inválido por construcción: imposible elegir una raíz porque no aparece.
- **`GET /ingredientes?es_alergeno=true`**: ya existía en el código, solo se formaliza en spec. Lo va a consumir el frontend para poblar el multi-select de alérgenos del filtro de catálogo.

### Por qué se necesita

Sin este change, el catálogo del cliente queda con filtros pobres y categorías inconsistentes:

1. **UX estilo MercadoLibre imposible sin filtro recursivo.** Si el cliente elige "Pizzas" (raíz) y solo aparecen los productos asignados *literalmente* a "Pizzas" — ignorando "Pizzas → Margheritas", "Pizzas → Especialidades" — el filtro es inútil. Forza al cliente a saber la categoría hoja exacta, lo cual derrota el propósito de tener jerarquía.
2. **Filtro de alérgenos binario es insuficiente para un sistema de COMIDAS.** Una persona celíaca y una persona con alergia al maní tienen restricciones distintas. Excluir "todo lo que tenga alérgenos no removibles" tira el 80% del catálogo aunque solo querés evitar gluten. El multi-select por alérgeno específico es requisito funcional, no nice-to-have.
3. **Integridad de la jerarquía de categorías.** Permitir que un producto se asigne a una categoría raíz convierte la jerarquía en una taxonomía mentirosa: "Bebidas" deja de ser un agrupador y pasa a competir con sus hijas. El sistema tiene que defender que solo las hojas son válidas para asignación; el frontend ayuda con `?solo_hojas=true`, pero la validación backend es la red de seguridad.
4. **Edge case del cascadeo.** Sin el block-on-promote, el día que un admin agregue una subcategoría a una hoja con productos asignados, esos productos quedan con categoría inválida y `disponible=false` silenciosamente. Bloquear la creación es coherente y obliga al admin a tomar la decisión consciente.

---

## 1. `products-frontend-catalog` — Sprint 7

### En qué consiste

Primer UI funcional sobre el backend completo: el catálogo público que el cliente usa para descubrir productos antes de armar el carrito.

Alcance:

- **Página listado** `/cliente/catalogo`: grid de productos con paginación server-side, skeleton loaders, estados empty (sin productos / sin matches con filtros) y error con retry.
- **Página detalle** `/cliente/catalogo/:productoId`: nombre, descripción, precio, ingredientes con badge cuando son alérgenos, botón "Agregar al carrito" (que ya llama a `cartStore.addItem()` — la UI del carrito viene en Sprint 9).
- **FilterBar**:
  - Search debounced.
  - Categorías estilo ML: chips raíz arriba, al seleccionar una raíz se despliegan subchips con sus hijas hoja como filtros finos. El árbol viene de `GET /categorias`; se aplana del lado frontend.
  - Multi-select de alérgenos: poblado por `GET /ingredientes?es_alergeno=true`, manda `excluir_alergeno_ids[]` al backend.
- **URL como source-of-truth de filtros**: `useSearchParams()`. Refresh, back/forward y links compartidos preservan estado.
- **TanStack Query** para server state: `useProductos` (paginado), `useProductoDetail`, `useCategorias` (long staleTime — categorías cambian poco), `useAlergenos`.
- **Zod schemas** en `features/catalog/schemas/`. `precio` se coerce a `number` en el boundary del service (el backend lo manda como string Decimal `"12.50"` — si no se coerce, `getTotalPrice()` del cart devuelve `NaN`).

Out of scope: admin CRUD de productos, image upload, rango de precio (no hay param backend), drawer del carrito completo (Sprint 9).

### Por qué se necesita

Es la primera ventana del cliente al sistema. Hasta ahora todo lo que se construyó (auth, productos backend, pedidos backend, pagos backend) vivió detrás de Swagger UI. Este change da:

1. **Validación E2E del backend de productos.** El catálogo va a hacer surface de bugs de integración (formato de fecha, paginación, snapshots de precio en pedido) que con tests de backend solos no salen.
2. **Prerequisito de Sprint 9 (carrito).** Sin un lugar donde el cliente vea productos, no hay cómo agregarlos al carrito. La cadena `catálogo → carrito → checkout → pago` empieza acá.
3. **Demostración del integrador.** La rúbrica de la cátedra evalúa funcionalidad visible. El catálogo es la prueba más directa de que el sistema "funciona": el cliente entra, filtra, ve productos disponibles, agrega al carrito.
4. **Punto de salida para el resto de Fase B.** Patterns que se establecen acá (TanStack Query keys, URL state, Zod schemas, page composition) los reutilizan los 9 changes siguientes. Hacerlo bien ahora ahorra refactors después.

---

## 2. `user-profile-frontend` — Sprint 8

### En qué consiste

Página de perfil del cliente autenticado: ver y editar datos personales, cambiar contraseña, ver el email (read-only).

Alcance:

- **`/cliente/perfil`** con dos secciones: "Datos personales" (formulario inline) y "Seguridad" (botón → modal cambio contraseña).
- **Formulario de edición**: nombre, apellido. Email es read-only (cambiar email implica reverificación, fuera de scope). TanStack Form + Zod schema reutilizable de `auth/schemas`.
- **Modal cambio de contraseña**: campos contraseña actual + nueva + confirmar nueva. Validación local (mínimo 8 chars, ambos nuevos iguales). Después de submit OK → muestra toast + **fuerza re-login** porque el backend invalida todos los refresh tokens del usuario (RN de seguridad). El interceptor de 401 ya lo cubre, pero la UI tiene que mostrar el mensaje "cambiaste tu contraseña, volvé a entrar".

### Por qué se necesita

1. **Confianza del usuario**. Un sistema con cuenta sin la posibilidad de ver/editar el perfil se siente broken. Es UX mínima esperada.
2. **Compliance básico con buenas prácticas de seguridad**. Permitir que el usuario rote su contraseña sin contactar soporte es un requisito que la cátedra puede evaluar.
3. **Pequeño y bajo riesgo**. Backend ya está, el frontend es ~2hs — sirve para fluidificar después del catálogo (que es más grande) y mantener momentum sin sprints back-to-back grandes.

---

## 3. `delivery-addresses-frontend` — Sprint 8

### En qué consiste

CRUD de direcciones de delivery del cliente. Sin él, el flujo de checkout no funciona porque el cliente no tiene dónde recibir el pedido.

Alcance:

- **`/cliente/direcciones`** con lista de direcciones del cliente: dirección calle + número + piso + depto + referencia + flag "predeterminada".
- **Formulario alta/edición** (modal o inline): inputs Zod-validados, autocomplete opcional con geocoding (descartado por ahora — input libre).
- **Acciones por ítem**: editar, marcar predeterminada, eliminar (soft-delete backend).
- **Reutilización en checkout**: el componente "selector de dirección" del checkout (Sprint 9) reusa los mismos hooks y schemas.
- TanStack Query para invalidación: alta/edición/delete → `queryClient.invalidateQueries(['addresses'])`.

### Por qué se necesita

1. **Prerequisito duro del checkout** (Sprint 9 #26). El cliente no puede confirmar un pedido sin elegir una dirección. Sin este change, todo el flujo de compra queda bloqueado.
2. **Reutilización pesada en checkout**. Los componentes que se crean acá (`AddressCard`, `AddressForm`, `useAddresses`) los consume `order-creation-frontend-checkout` casi sin cambios. Hacerlo separado mantiene los scopes limpios y permite cerrar Sprint 8 antes de entrar al sprint más grande del proyecto.

---

## 4. `shopping-cart-zustand` — Sprint 9

### En qué consiste

UI completa del carrito de compras (el store ya existe desde `frontend-rebuild-on-feature-first`). Drawer lateral, edición de cantidades, personalización de ingredientes removibles, total dinámico.

Alcance:

- **CartDrawer** (ya existe el shell desde el rebuild, falta contenido real): lista de items con imagen, nombre, precio, cantidad editable (`+` / `-` / input numérico), botón remove. Total al pie con CTA "Ir al checkout".
- **Personalización por item**: si un ingrediente está marcado `es_removible=true` en `ProductoIngrediente`, el cliente puede "sacar" ese ingrediente. La selección se guarda en `CartItem.personalizacion: { quitados: number[] }`.
- **Cálculo de total**: side-effect-free, derivado de los items con `getTotalPrice()`. Coerción de `precio` ya viene resuelta del Sprint 7.
- **Persistencia**: localStorage con la key `food-store-cart` (configurada). Sobrevive logout (decisión de UX explícita: el carrito es del navegador, no de la sesión).
- **Sin backend**: 100% client-side. El backend solo aparece cuando se crea el pedido (Sprint 9 #26).

### Por qué se necesita

1. **Cierre del loop catálogo → carrito**. Sin UI de carrito, el botón "Agregar" del catálogo no tiene feedback más allá del badge del TopNavbar. El cliente necesita ver qué agregó, ajustar cantidades y revisar antes de comprar.
2. **Personalización es valor diferencial**. La spec marca ingredientes removibles como feature. Sin la UI, el feature no existe. Es lo que diferencia este sistema de un menú estático.

---

## 5. `checkout-validation-frontend` — Sprint 9

### En qué consiste

Capa de validación que corre ANTES de intentar crear el pedido en el backend. Atrapa cambios de stock, precio o disponibilidad que pasaron entre que el cliente armó el carrito y apretó "Confirmar".

Alcance:

- **Hook `useCheckoutValidation(cartItems)`**: dispara un `POST /productos/validar-carrito` (endpoint a confirmar — si no existe, se usa un loop de `GET /productos/{id}` en paralelo) que devuelve por ítem: disponibilidad actual, stock actual, precio actual.
- **Detección de divergencias**:
  - Producto pasó a `disponible=false` → bloquea el checkout para ese item, sugerir removerlo.
  - Stock bajó por debajo de la cantidad pedida → ofrecer reducir cantidad o remover.
  - Precio cambió → modal "el precio de X subió de $A a $B, ¿continuás?".
- **Modal de confirmación**: muestra el total final con los snapshots vigentes y un CTA explícito "Sí, confirmar pedido".
- **Notificaciones**: toasts inline en cada item afectado, no solo errores globales.

### Por qué se necesita

1. **UX honesta**. Crear un pedido y que el backend lo rechace con 409 después es la peor experiencia posible. Validar antes y mostrar mensajes específicos por ítem evita la frustración.
2. **Reduce carga al backend**. El backend tiene que validar igual (no se confía en el cliente), pero acá se filtran los casos triviales y se mejora la latencia percibida.
3. **Cubrir RN-PE/RN-CH**: las reglas de negocio sobre snapshots y validación en checkout no son negociables para la rúbrica.

---

## 6. `order-creation-frontend-checkout` — Sprint 9

### En qué consiste

Page final del flujo de compra: selección de dirección, resumen de items con snapshots, total, botón "Crear pedido". Después del POST exitoso, redirige al detalle del pedido o a la pantalla de pago según el flujo.

Alcance:

- **`/cliente/checkout`** (nueva ruta): wizard de un paso (no multi-step — todo en una pantalla).
- **Composición**: `AddressSelector` (reusa del Sprint 8) + `CartSummary` (lista read-only con snapshots) + `PaymentMethodPicker` placeholder (Sprint 10 lo completa) + `ConfirmButton`.
- **Flujo POST**: arma payload con `direccion_id`, lista de items y precios snapshot, dispara `POST /pedidos`. Si OK → invalida `['cart']` (clear) + invalida `['orders']` + redirige a `/cliente/pedidos/:id`.
- **Manejo de errores específicos**: 409 stock insuficiente → vuelve a la pantalla con el item marcado en rojo. 422 dirección inválida → vuelve al selector.

### Por qué se necesita

1. **Cierre del flujo de compra cliente**. Después de este change el cliente puede COMPRAR (sin pagar todavía, ese es Sprint 10). Es el primer momento donde la rúbrica puede demostrarse end-to-end con un cliente real.
2. **Punto de integración masivo**. Es el change que ata productos + carrito + direcciones + pedidos. Cualquier bug de contract entre features sale acá.

---

## 7. `payment-mercadopago-frontend` — Sprint 10

### En qué consiste

Integración del SDK de MercadoPago en el frontend para pagar pedidos pendientes. Cierre del ciclo `PENDIENTE → CONFIRMADO`.

Alcance:

- **SDK MercadoPago.js** cargado dinámicamente (no en el bundle inicial — solo en `/cliente/checkout` cuando entra a paso pago).
- **Tokenización PCI SAQ-A**: el SDK toma los datos de tarjeta directamente y devuelve un token. Los datos sensibles **no pasan por nuestro backend**. El frontend solo manda el token + `preferencia_id` al backend.
- **Flujo**:
  1. Frontend ya tiene un pedido creado (Sprint 9 #26).
  2. Pide al backend `POST /pagos/preferencia/{pedido_id}` → recibe `preference_id` de MP.
  3. Renderiza el form de MP con ese `preference_id`.
  4. Usuario completa tarjeta → MP devuelve token → frontend manda al backend `POST /pagos/procesar`.
  5. Backend valida con MP y emite webhook interno → estado del pedido pasa a `CONFIRMADO`.
- **Polling/listener**: después del POST, el frontend pollea `GET /pedidos/{id}` cada 2s hasta que el estado pase a `CONFIRMADO` o `RECHAZADO`. Timeout 30s con CTA "Refrescar".
- **Sandbox-only**: usa credenciales MP Test (las de prod requieren homologación que está fuera del alcance del integrador).

### Por qué se necesita

1. **Es la mitad faltante del par pago**. El backend ya tiene `payment-mercadopago-backend` archivado; sin el frontend no se valida E2E que la integración funciona. La cátedra evalúa el flujo completo, no las mitades.
2. **PCI compliance por construcción**. Hacer la tokenización del lado del cliente nos saca del scope PCI más exigente (SAQ-D). Implementarlo mal — pasar tarjetas por el backend — convierte el proyecto en un riesgo real, no solo académico.

---

## 8. `order-visualization-frontend` — Sprint 11

### En qué consiste

Dos vistas: "Mis pedidos" (cliente, ve sus propios pedidos) y "Gestión de pedidos" (gestor con rol PEDIDOS, ve y maneja todos los pedidos).

Alcance:

- **`/cliente/pedidos`** (lista cliente): tabla / cards con número, fecha, estado actual, total. Click → `/cliente/pedidos/:id` con timeline de estados, items, dirección, info de pago.
- **`/admin/pedidos`** (lista gestor): tabla con filtros (estado, rango de fecha, cliente search), paginación server-side. Click → detalle full con **botones para transicionar estado** según la FSM ya implementada (RECIBIDO → EN_PREPARACION → LISTO → EN_CAMINO → ENTREGADO; o → CANCELADO desde estados permitidos).
- **Timeline visual**: componente reusable que muestra el historial de estados del pedido con timestamps y `motivo` cuando aplica (cancelaciones, etc.).
- **Polling opcional**: refresca la lista cada 30s si el rol es PEDIDOS (gestor activo).

### Por qué se necesita

1. **Visibilidad post-pago**. Después de pagar, el cliente necesita saber qué pasa con su pedido. Sin esta vista, el flujo termina ciegamente en "gracias".
2. **Operatividad del staff**. La FSM ya está implementada en backend pero sin UI los gestores no la pueden mover. Es lo que convierte el sistema de "demo" en "operativo".
3. **Demostración FSM**. La rúbrica le da peso al ciclo de vida del pedido. Mostrarlo visualmente con el timeline es la forma más directa de probar que la lógica de estados funciona.

---

## 9. `admin-users-frontend` — Sprint 12

### En qué consiste

Panel admin para gestionar usuarios del sistema: ver lista, editar datos, asignar roles, desactivar cuentas.

Alcance:

- **`/admin/usuarios`**: tabla paginada con search (nombre, email), filtros (rol, estado), columnas (id, nombre completo, email, roles, estado, creado_en).
- **Modal editar**: cambio de nombre/apellido. Email read-only (mismo principio que perfil cliente).
- **Modal cambiar rol**: asignar / remover roles ADMIN, STOCK, PEDIDOS, CLIENT. Multi-select. Solo ADMIN puede ascender otro ADMIN (RN-AU).
- **Acción desactivar**: soft-delete (`is_active=false`). El usuario no puede loguearse mientras esté desactivado. Reversible — botón "reactivar".
- **Sin self-edit**: el admin no puede cambiarse roles a sí mismo (defensa contra lock-out).

### Por qué se necesita

1. **Operatividad del sistema multi-rol**. El backend ya tiene roles ADMIN/STOCK/PEDIDOS/CLIENT, pero sin esta UI solo se asignan a mano por SQL. No se puede operar el sistema sin gestión de usuarios.
2. **Cubrir la US-053..055**. Historias de gestión de usuarios son requisito explícito de la rúbrica.

---

## 10. `admin-dashboard-frontend` — Sprint 12

### En qué consiste

Dashboard con visualizaciones de las métricas del negocio. Es el último change del integrador: el "tablero" que cierra la experiencia admin.

Alcance:

- **`/admin/metricas`**: layout grid con 4-6 widgets.
- **Widgets**:
  - Ventas por periodo (gráfico de línea con `recharts`): filtro de fecha (día, semana, mes), eje X = fecha, eje Y = total $.
  - Top productos (bar chart): productos más vendidos en el rango seleccionado.
  - Distribución por estado de pedidos (pie chart): porcentaje en cada estado de la FSM.
  - Ticket promedio (KPI grande): total ventas / cantidad pedidos.
  - Pedidos por hora (heatmap u histograma): identificar picos del día.
- **Source de datos**: `GET /admin/metricas/*` endpoints ya archivados.
- **Acá entra el CRUD admin de productos también** (aunque históricamente quedó out-of-scope del sprint dashboard): listado, alta, edición, soft-delete, gestión de stock y disponibilidad. Si crece mucho, se separa en un change distinto antes del proposal.

### Por qué se necesita

1. **Inteligencia de negocio en vivo**. Los endpoints de métricas ya existen; sin esta UI quedan invisibles. El dashboard convierte datos crudos en decisiones.
2. **Cierre visible del integrador**. Un dashboard con gráficos cierra la sensación de "producto terminado". Es el último frente que la cátedra ve y el que más impresión genera respecto al pulido.
3. **CRUD admin de productos por convergencia**. Es lo único que falta para que el admin pueda operar el catálogo sin tocar el backend directamente. Si el dashboard queda chico (3-4hs), se mete en el mismo change; si crece, se separa.

---

## 11. `system-configuration` — Postergable

### En qué consiste

Panel admin para parámetros globales del sistema (horarios de atención, zona de entrega, otros key-value).

Alcance:

- Tabla `system_config` key-value en BD (Alembic migration).
- Endpoints REST simples para get/set por key.
- UI admin con formulario por key configurable.

### Por qué se necesita (y por qué se postergó)

- **Por qué se necesita**: hay parámetros que no quieren vivir hardcoded (horario de atención, días de descanso, radio de delivery).
- **Por qué se postergó**: ninguna funcionalidad de Sprint 7-12 depende de esto. Si hay tiempo después del dashboard, se hace. Si no, queda como deuda documentada y se hardcodean los parámetros con `TODO: extract to system_config`.

---

## Estimaciones agregadas

| Sprint | Changes | Duración estimada |
|--------|---------|-------------------|
| 7      | 1 (catálogo) | 4-5 hs |
| 8      | 2 (perfil + direcciones) | 4-5 hs |
| 9      | 3 (carrito + checkout val + creación) | 7-10 hs |
| 10     | 1 (pagos MP) | 3-4 hs |
| 11     | 1 (visualización pedidos) | 4-5 hs |
| 12     | 2 (admin users + dashboard/CRUD) | 5-7 hs |
| **Total Fase B** | **10 changes** | **27-36 hs** |

Más `catalog-filters-and-leaf-categories-backend` (recién implementado, ~1-2 hs efectivas) que es pre-bloqueante de Sprint 7.

---

## Cómo usar este documento

1. **Antes de proponer un change**: leer su sección acá para tener la intención y el "por qué" claros. El sub-agent de `/opsx:propose` consume este contexto.
2. **Si el alcance cambia durante el proposal**: actualizar la sección correspondiente acá *antes* de cerrar la proposal — el doc tiene que reflejar la realidad.
3. **Si un change se postpone o se split**: marcar en la sección con `> ⚠️ Reorganizado YYYY-MM-DD: ver <nuevo nombre>` y dejar el contexto histórico.
4. **Cuando un change se archive**: agregar al final de su sección `> ✅ Archivado YYYY-MM-DD: ver openspec/changes/archive/`.

Mantener este doc al día es barato (es texto) y ahorra muchas idas y vueltas en cada proposal nuevo.
