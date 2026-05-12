# Mapa de Changes — Food Store v5.0

## Introducción

Un **change** es la unidad mínima de trabajo en SDD. Cada change es un conjunto de tres artefactos:
- **proposal.md**: QUÉ se va a construir y POR QUÉ
- **design.md**: CÓMO técnicamente (arquitectura, modelos, endpoints)
- **tasks.md**: Checklist atómica de implementación

Este documento define el mapa completo de **30 changes** para desarrollar Food Store de principio a fin, organizados en orden de implementación.

### Estrategia: Backend-First → Frontend-First

El proyecto se desarrolla en **dos fases secuenciales**:

- **FASE A — Backend completo (Sprints 0–6)**: Se construye toda la API REST con tests de integración fuertes. La validación es 100% automatizada (`pytest`) y manual (Postman/curl). Sin UI hasta el final de esta fase.
- **FASE B — Frontend completo (Sprints 7–12)**: Una vez que el backend está estable y testeado, se construye toda la UI sobre una API congelada.

**Tradeoff aceptado**: la validación E2E se concentra en la Fase B. Los bugs de integración (CORS, formatos de fecha, paginación, snapshots) aparecerán de golpe al arrancar el frontend. Para mitigarlo, los tests de integración del backend deben cubrir todos los caminos críticos.

### Estado actual (2026-05-12)

- **Sprints 0 a 4**: ✅ Archivados completos (changes #1 al #13)
- **Refactors**: ✅ Archivados — `refactor-uow-to-context-manager` (68/68), `refactor-auth-to-uow`, `refactor-users-route-to-spanish`
- **Sprint 5**: 🔄 En progreso — `order-creation-backend` (#14) ✅ archivado, `payment-mercadopago-backend` (#15) ✅ archivado, `order-state-machine-fsm` (#16) 🔄 En implementación

---

# FASE A — Backend Completo

## Sprint 0 — Infraestructura Base ✅ ARCHIVADO

### 1. **setup-backend-core** ✅
- **Funcionalidad**: Scaffolding del backend, estructura feature-first, dependencias FastAPI, configuración inicial
- **Historias**: US-000, US-000a
- **Dependencias**: Ninguna

### 2. **setup-frontend-core** ✅
- **Funcionalidad**: Scaffolding del frontend, estructura FSD, dependencias React/Vite, configuración Tailwind
- **Historias**: US-000, US-000c
- **Dependencias**: Ninguna
- **Nota**: Adelantado en Sprint 0 para no bloquear la Fase B después.

### 3. **database-schema-seed** ✅
- **Funcionalidad**: Todas las tablas del ERD v5, migraciones Alembic, script de seed (Roles, EstadoPedidos, FormaPago, usuario admin)
- **Historias**: US-000b, US-000d
- **Dependencias**: setup-backend-core

### 4. **backend-error-handling-validation** ✅
- **Funcionalidad**: RFC 7807 (Problem Details), manejo de excepciones global, validación Pydantic v2, sanitización de inputs
- **Historias**: US-068, US-074
- **Dependencias**: setup-backend-core

### 5. **zustand-stores-base** ✅
- **Funcionalidad**: Cuatro stores de Zustand: authStore, cartStore, paymentStore, uiStore (todos tipados, con persist)
- **Historias**: US-000e
- **Dependencias**: setup-frontend-core
- **Nota**: Adelantado en Sprint 0 para que el frontend tenga base lista cuando arranque la Fase B.

---

## Sprint 1 — Autenticación y Autorización ✅ ARCHIVADO

### 6. **auth-backend** ✅
- **Funcionalidad**: Login, registro, JWT (access+refresh), refresh automático, logout, RBAC (require_role), rate limiting, BaseRepository + UnitOfWork
- **Historias**: US-001, US-002, US-003, US-004, US-005, US-006, US-073
- **Dependencias**: database-schema-seed, backend-error-handling-validation

### 7. **auth-frontend-interceptor** ✅
- **Funcionalidad**: Formularios de login/registro, interceptor Axios para JWT, renovación automática en 401, toast de errores, authStore integration
- **Historias**: US-001, US-002, US-066, US-067
- **Dependencias**: auth-backend, zustand-stores-base, setup-frontend-core
- **Nota**: Adelantado para validar el contrato del auth-backend con UI real.

### 8. **navigation-routing-base** ✅
- **Funcionalidad**: Layout base, navbar/sidebar adaptado por rol, react-router con guards, rutas públicas/privadas, componentes de error (403, 404)
- **Historias**: US-075, US-076
- **Dependencias**: auth-frontend-interceptor

---

## Sprint 2 — Catálogo Base ✅ ARCHIVADO

### 9. **categories-backend** ✅
- **Funcionalidad**: CRUD completo de categorías, jerarquía recursiva con CTE, soft delete, validación de ciclos
- **Historias**: US-007, US-008, US-009, US-010
- **Dependencias**: auth-backend
- **Duración**: 3-4 horas

### 10. **ingredients-backend** ✅
- **Funcionalidad**: CRUD de ingredientes, campo es_alergeno, soft delete, filtrados por alérgeno
- **Historias**: US-011, US-012, US-013, US-014
- **Dependencias**: auth-backend
- **Duración**: 2-3 horas

---

## Sprint 3 — Productos (Backend) ✅ ARCHIVADO

### 11. **products-backend** ✅
- **Funcionalidad**: CRUD de productos, asociación M2M con categorías e ingredientes, stock management, soft delete, endpoint público con filtros
- **Historias**: US-015, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023
- **Dependencias**: categories-backend, ingredients-backend
- **Razón**: El corazón del catálogo. Bloquea casi toda la Fase A restante.
- **Duración estimada**: 5-6 horas

---

## Sprint 4 — Perfil y Direcciones (Backend) ✅ ARCHIVADO

### 12. **user-profile-backend** ✅
- **Funcionalidad**: GET /me, PUT /me (datos personales), POST /me/password (cambio de contraseña con validación de la actual), invalidación de refresh tokens en cambio de password
- **Historias**: US-061, US-062, US-063
- **Dependencias**: auth-backend
- **Razón**: Endpoints básicos de cualquier usuario autenticado.
- **Duración estimada**: 2 horas

### 13. **delivery-addresses-backend** ✅
- **Funcionalidad**: CRUD de direcciones, dirección predeterminada, ownership validation, endpoint GET único del cliente, PATCH /principal
- **Historias**: US-024, US-025, US-026, US-027, US-028
- **Dependencias**: auth-backend
- **Razón**: Necesarias antes de crear pedidos. Bloquea order-creation-backend.
- **Duración estimada**: 2-3 horas

---

## Refactors — Fuera del roadmap original ✅ ARCHIVADOS

### ✅ **refactor-uow-to-context-manager**
- **Funcionalidad**: Migrar el lifecycle del UnitOfWork de los routers a los services usando context manager. Elimina `Depends(get_uow)`, traslada `commit()`/`rollback()` al service, y resuelve el "double-read pattern" en routers.
- **Justificación**: Deuda técnica reconocida en los design.md archivados de Sprints 2-4. El patrón actual mezcla preocupaciones HTTP con transaccionales.
- **Dependencias**: categories-backend, ingredients-backend, products-backend, user-profile-backend, delivery-addresses-backend
- **Estado**: ✅ 68/68 tasks completadas — Archivado

### ✅ **refactor-auth-to-uow**
- **Funcionalidad**: Migrar AuthService al patrón service-driven UoW. Cierra bug latente de atomicidad en register, elimina `Depends(get_db)`.
- **Estado**: ✅ Archivado

### ✅ **refactor-users-route-to-spanish**
- **Funcionalidad**: Alinear ruta HTTP `/api/v1/users` → `/api/v1/usuarios` según lexicón español del integrador §5.
- **Estado**: ✅ Archivado

---

## Sprint 5 — Ciclo de Vida del Pedido (Backend)

### 14. **order-creation-backend** ✅
- **Funcionalidad**: Endpoint POST /pedidos, creación atómica con UoW, snapshots de precio y dirección, validación de stock dentro de transacción, HistorialEstadoPedido inicial, estado PENDIENTE
- **Historias**: US-035, US-036, US-037, US-038
- **Dependencias**: delivery-addresses-backend, products-backend, database-schema-seed
- **Razón**: Core del negocio. Operación más compleja del backend — múltiples inserts atómicos.
- **Duración estimada**: 5-6 horas

### 15. **payment-mercadopago-backend**
- **Funcionalidad**: Endpoint crear preferencia/orden, webhook IPN (/webhooks/mercadopago), idempotency_key UUID, transición automática PENDIENTE→CONFIRMADO, tabla Pago completa
- **Historias**: US-045, US-046, US-047, US-048 (parte backend)
- **Dependencias**: order-creation-backend
- **Razón**: La mitad servidora del flujo de pago. La tokenización (SDK MercadoPago.js) queda para la Fase B.
- **Validación**: ngrok + Postman para simular el webhook IPN. El flujo completo no se valida hasta el frontend.
- **Duración estimada**: 4-5 horas

### 16. **order-state-machine-fsm**
- **Funcionalidad**: FSM completa (PENDIENTE, CONFIRMADO, EN_PREPARACIÓN, EN_CAMINO, ENTREGADO, CANCELADO), transiciones validadas en Service, decremento de stock en CONFIRMADO, restauración en CANCELADO, HistorialEstadoPedido append-only
- **Historias**: US-039, US-040, US-041, US-042, US-043, US-044
- **Dependencias**: payment-mercadopago-backend
- **Razón**: Define todo el ciclo de vida del pedido. Endpoints para que gestores avancen estados.
- **Duración estimada**: 5-6 horas

### 17. **order-visualization-backend**
- **Funcionalidad**: GET /pedidos (listado filtrado por usuario si es CLIENT, todos si ADMIN/PEDIDOS), GET /pedidos/{id} con snapshots y historial, paginación, filtros por estado y fecha
- **Historias**: US-049, US-050, US-051, US-052
- **Dependencias**: order-state-machine-fsm
- **Razón**: Endpoints read-only para clientes y gestores.
- **Duración estimada**: 3-4 horas

---

## Sprint 6 — Administración (Backend)

### 18. **admin-users-backend**
- **Funcionalidad**: GET /admin/usuarios (listado paginado), PUT /admin/usuarios/{id} (editar), PATCH /admin/usuarios/{id}/rol (cambiar rol), PATCH /admin/usuarios/{id}/estado (desactivar), búsqueda por email/nombre, filtro por rol, validación de no quitar último ADMIN
- **Historias**: US-053, US-054, US-055
- **Dependencias**: auth-backend
- **Razón**: Admin necesita controlar usuarios del sistema.
- **Duración estimada**: 2-3 horas

### 19. **admin-catalog-permissions**
- **Funcionalidad**: Extender endpoints de productos, categorías e ingredientes para aceptar tanto ADMIN como STOCK/PEDIDOS según corresponda. Admin tiene acceso completo a gestionar todo.
- **Historias**: US-064, US-065
- **Dependencias**: products-backend, order-state-machine-fsm, admin-users-backend
- **Razón**: Admin necesita poder intervenir en catálogo y pedidos sin depender del gestor.
- **Duración estimada**: 1-2 horas

### 20. **admin-metrics-backend**
- **Funcionalidad**: GET /admin/metricas/resumen, agregaciones de ventas por periodo, top productos más vendidos, distribución por estado, filtro por fecha
- **Historias**: US-056, US-057, US-058, US-059 (parte backend)
- **Dependencias**: order-creation-backend (datos)
- **Razón**: Inteligencia del negocio. Solo endpoints — la visualización con recharts va a la Fase B.
- **Duración estimada**: 2-3 horas

---

# FASE B — Frontend Completo

A partir de acá la API está congelada y todos los changes son frontend-only.

---

## Sprint 7 — Catálogo (Frontend)

### 21. **products-frontend-catalog**
- **Funcionalidad**: Listado de productos (catálogo público), detalle de producto, filtros (categoría, búsqueda, rango de precio, alérgenos), paginación, skeleton loaders, TanStack Query
- **Historias**: US-018, US-019, US-023
- **Dependencias**: products-backend ✅, navigation-routing-base ✅
- **Razón**: Primera UI funcional sobre el backend completo. Validación E2E del catálogo.
- **Duración estimada**: 4-5 horas

---

## Sprint 8 — Perfil y Direcciones (Frontend)

### 22. **user-profile-frontend**
- **Funcionalidad**: Página de perfil, formulario de edición de datos, modal de cambio de contraseña, manejo de invalidación de tokens (re-login)
- **Historias**: US-061, US-062, US-063
- **Dependencias**: user-profile-backend ✅, navigation-routing-base ✅
- **Duración estimada**: 2 horas

### 23. **delivery-addresses-frontend**
- **Funcionalidad**: Lista de direcciones del cliente, formulario alta/edición, marcar predeterminada, eliminar
- **Historias**: US-024, US-025, US-026, US-027, US-028
- **Dependencias**: delivery-addresses-backend ✅
- **Duración estimada**: 2-3 horas

---

## Sprint 9 — Carrito y Checkout (Frontend)

### 24. **shopping-cart-zustand**
- **Funcionalidad**: Store Zustand completo (addItem, removeItem, updateQuantity, clearCart), persistencia en localStorage, personalización de ingredientes, cálculo de totales
- **Historias**: US-029, US-030, US-031, US-032, US-033, US-034
- **Dependencias**: products-frontend-catalog, zustand-stores-base ✅
- **Razón**: 100% client-side. No hay backend para esto.
- **Duración estimada**: 2-3 horas

### 25. **checkout-validation-frontend**
- **Funcionalidad**: Validación pre-checkout (stock, disponibilidad), detección de cambios de precio, modal de confirmación, notificaciones al cliente
- **Historias**: US-069, US-070
- **Dependencias**: shopping-cart-zustand, products-backend ✅
- **Razón**: Validar ANTES de intentar crear el pedido. Mejor UX.
- **Duración estimada**: 2-3 horas

### 26. **order-creation-frontend-checkout**
- **Funcionalidad**: Componentes de checkout (selección de dirección, confirmación de items con snapshots, resumen de total), flujo post-creación, confirmación visual
- **Historias**: US-035, US-071
- **Dependencias**: order-creation-backend ✅, checkout-validation-frontend, delivery-addresses-frontend
- **Razón**: UI para que el cliente confirme y cree el pedido.
- **Duración estimada**: 3-4 horas

---

## Sprint 10 — Pagos (Frontend)

### 27. **payment-mercadopago-frontend**
- **Funcionalidad**: SDK MercadoPago.js (tokenización PCI SAQ-A), formulario de pago, integración con preferencia generada por backend, redirección post-pago, polling/listener para confirmación de estado
- **Historias**: US-045, US-046, US-047, US-048 (parte frontend)
- **Dependencias**: payment-mercadopago-backend ✅, order-creation-frontend-checkout
- **Razón**: Cierra el flujo de pago. Acá se valida E2E todo el ciclo PENDIENTE→CONFIRMADO con MP Sandbox.
- **Duración estimada**: 3-4 horas

---

## Sprint 11 — Visualización de Pedidos (Frontend)

### 28. **order-visualization-frontend**
- **Funcionalidad**: Página "Mis Pedidos" (cliente), panel de gestión de pedidos (gestor), detalles con timeline de estados, historial, información de pago, botones para cambiar estado (solo gestor)
- **Historias**: US-049, US-050, US-051, US-052, US-072
- **Dependencias**: order-visualization-backend ✅, order-state-machine-fsm ✅
- **Razón**: UI para que clientes vean sus pedidos y gestores gestionen estados.
- **Duración estimada**: 4-5 horas

---

## Sprint 12 — Administración (Frontend)

### 29. **admin-users-frontend**
- **Funcionalidad**: Panel de usuarios con tabla paginada, filtros, búsqueda, modales para editar / cambiar rol / desactivar
- **Historias**: US-053, US-054, US-055
- **Dependencias**: admin-users-backend ✅, navigation-routing-base ✅
- **Duración estimada**: 2-3 horas

### 30. **admin-dashboard-frontend**
- **Funcionalidad**: Panel de métricas con recharts, gráfico de ventas por periodo, top productos, distribución por estado, filtro por fecha
- **Historias**: US-056, US-057, US-058, US-059
- **Dependencias**: admin-metrics-backend ✅
- **Razón**: Cierra la experiencia admin con visualización completa.
- **Duración estimada**: 3-4 horas

---

# Postergable (fuera de las dos fases)

### **system-configuration** *(Baja prioridad)*
- **Funcionalidad**: Panel de configuración global (horarios, zona de entrega, parámetros), tabla key-value en BD, endpoints + UI
- **Historias**: US-060
- **Dependencias**: auth-backend ✅
- **Razón**: Baja prioridad. Solo se aborda si queda tiempo después del Sprint 12; si no, queda documentado como deuda.
- **Duración estimada**: 2-3 horas

---

## Grafo de Dependencias (post-reorganización)

```
FASE A — Backend
================

categories-backend ✅
└─ products-backend ──┐
ingredients-backend ✅┘
                      │
products-backend ─────┼─ admin-catalog-permissions
                      │
delivery-addresses-backend ─┐
                            ├─ order-creation-backend
products-backend ───────────┘
                                  │
                                  └─ payment-mercadopago-backend
                                        │
                                        └─ order-state-machine-fsm
                                              ├─ order-visualization-backend
                                              └─ admin-catalog-permissions

user-profile-backend (auth)
admin-users-backend (auth) ─ admin-catalog-permissions
admin-metrics-backend (depende: order-creation-backend)


FASE B — Frontend
=================

products-frontend-catalog (products-backend ✅)
└─ shopping-cart-zustand
   └─ checkout-validation-frontend
      └─ order-creation-frontend-checkout
         └─ payment-mercadopago-frontend (payment-backend ✅)

user-profile-frontend (user-profile-backend ✅)
delivery-addresses-frontend (delivery-addresses-backend ✅)
└─ order-creation-frontend-checkout

order-visualization-frontend (visualization-backend ✅)
admin-users-frontend (admin-users-backend ✅)
admin-dashboard-frontend (admin-metrics-backend ✅)
```

---

## Resumen por Sprint

| Fase | Sprint | Changes | Duración | Estado |
|------|--------|---------|----------|--------|
| A | **0** | setup-backend-core, setup-frontend-core, database-schema-seed, backend-error-handling-validation, zustand-stores-base | 12-16h | ✅ Archivado |
| A | **1** | auth-backend, auth-frontend-interceptor, navigation-routing-base | 11-14h | ✅ Archivado |
| A | **2** | categories-backend, ingredients-backend | 5-7h | ✅ Archivado |
| A | **3** | products-backend | 5-6h | ✅ Archivado |
| A | **4** | user-profile-backend, delivery-addresses-backend | 4-5h | ✅ Archivado |
| — | **Refactors** | refactor-uow-to-context-manager, refactor-auth-to-uow, refactor-users-route-to-spanish | — | ✅ Archivados |
| A | **5** | order-creation-backend ✅, payment-mercadopago-backend, order-state-machine-fsm, order-visualization-backend | 17-21h | 🔄 En progreso |
| A | **6** | admin-users-backend, admin-catalog-permissions, admin-metrics-backend | 5-8h | Pendiente |
| B | **7** | products-frontend-catalog | 4-5h | Pendiente |
| B | **8** | user-profile-frontend, delivery-addresses-frontend | 4-5h | Pendiente |
| B | **9** | shopping-cart-zustand, checkout-validation-frontend, order-creation-frontend-checkout | 7-10h | Pendiente |
| B | **10** | payment-mercadopago-frontend | 3-4h | Pendiente |
| B | **11** | order-visualization-frontend | 4-5h | Pendiente |
| B | **12** | admin-users-frontend, admin-dashboard-frontend | 5-7h | Pendiente |
| — | Postergable | system-configuration | 2-3h | Opcional |

**Total estimado**: 88-116 horas (30 changes)

---

## Convenciones del Proyecto

- **Package manager**: `pnpm` para todo el frontend (NO npm ni yarn). Todos los comandos en specs, tasks y documentación deben usar `pnpm`.
- **Backend**: Python con `pip` y `requirements.txt`.

## Reglas Importantes

- **Nunca implementes sin artefactos**: Si no existe `proposal.md` y `design.md` aprobados, no hay `/opsx:apply`.
- **El orden importa**: Si el change B necesita código del change A, A debe estar archivado antes.
- **Un change = un commit** (o varios commits atómicos). Nunca mezcles dos changes.
- **Las specs son código**: Se versionan en git, se revisan en PRs, evolucionan con el proyecto.
- **Backend-first significa tests-fuertes**: Sin UI para validar visualmente, los tests de integración del backend son la única red de seguridad. Cobertura mínima de los caminos críticos en cada change de Fase A.

---

## Próximos Pasos

1. **Proponer `payment-mercadopago-backend`** (#15) — `/opsx:propose payment-mercadopago-backend`.
2. Continuar la Fase A change por change: `order-state-machine-fsm` (#16) → `order-visualization-backend` (#17) → Sprint 6.
3. Sin desviarse al frontend hasta cerrar el Sprint 6.
4. Cada change genera proposal.md, design.md y tasks.md con `/opsx:propose <nombre>`.
5. Revisar artefactos antes de implementar.
6. Ejecutar `/opsx:apply <nombre>` cuando esté aprobado.
7. Ejecutar `/opsx:archive <nombre>` solo después de revisión humana.

¡Adelante!
