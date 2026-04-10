# Mapa de Changes — Food Store v5.0

## Introducción

Un **change** es la unidad mínima de trabajo en SDD. Cada change es un conjunto de tres artefactos:
- **proposal.md**: QUÉ se va a construir y POR QUÉ
- **design.md**: CÓMO técnicamente (arquitectura, modelos, endpoints)
- **tasks.md**: Checklist atómica de implementación

Este documento define el mapa completo de **25 changes** para desarrollar Food Store de principio a fin, organizados en orden de implementación. Cada change respeta las dependencias y está agrupado en sprints lógicos.

---

## Sprint 0 — Infraestructura Base (5 changes)

### 1. **setup-backend-core**
- **Funcionalidad**: Scaffolding del backend, estructura feature-first, dependencias FastAPI, configuración inicial
- **Historias**: US-000, US-000a
- **Dependencias**: Ninguna
- **Razón**: Fundación sobre la que se construye todo. Sin esto, no hay backend.
- **Duración estimada**: 2-3 horas

### 2. **setup-frontend-core**
- **Funcionalidad**: Scaffolding del frontend, estructura FSD, dependencias React/Vite, configuración Tailwind
- **Historias**: US-000, US-000c
- **Dependencias**: Ninguna
- **Razón**: Fundación del frontend. Puede hacerse en paralelo con setup-backend-core.
- **Duración estimada**: 2-3 horas

### 3. **database-schema-seed**
- **Funcionalidad**: Todas las tablas del ERD v5, migraciones Alembic, script de seed (Roles, EstadoPedidos, FormaPago, usuario admin)
- **Historias**: US-000b, US-000d
- **Dependencias**: setup-backend-core
- **Razón**: Las tablas y datos base deben existir antes de implementar cualquier módulo funcional.
- **Duración estimada**: 3-4 horas

### 4. **backend-error-handling-validation**
- **Funcionalidad**: RFC 7807 (Problem Details), manejo de excepciones global, validación Pydantic v2, sanitización de inputs
- **Historias**: US-068, US-074
- **Dependencias**: setup-backend-core
- **Razón**: Patrón transversal que debe estar en lugar antes de que los routers comiencen a escribirse.
- **Duración estimada**: 2-3 horas

### 5. **zustand-stores-base**
- **Funcionalidad**: Cuatro stores de Zustand: authStore, cartStore, paymentStore, uiStore (todos tipados, con persist)
- **Historias**: US-000e
- **Dependencias**: setup-frontend-core
- **Razón**: Los stores son la base del estado del cliente en todo el frontend.
- **Duración estimada**: 2-3 horas

---

## Sprint 1 — Autenticación y Autorización (3 changes)

### 6. **auth-backend**
- **Funcionalidad**: Login, registro, JWT (access+refresh), refresh automático, logout, RBAC (require_role), rate limiting, BaseRepository + UnitOfWork
- **Historias**: US-001, US-002, US-003, US-004, US-005, US-006, US-073
- **Dependencias**: database-schema-seed, backend-error-handling-validation
- **Razón**: Sistema de seguridad central. Sin auth, no hay control de acceso en nada.
- **Duración estimada**: 5-6 horas

### 7. **auth-frontend-interceptor**
- **Funcionalidad**: Formularios de login/registro, interceptor Axios para JWT, renovación automática en 401, toast de errores, authStore integration
- **Historias**: US-001, US-002, US-066, US-067
- **Dependencias**: auth-backend, zustand-stores-base, setup-frontend-core
- **Razón**: Implementa el lado del cliente del flujo de autenticación.
- **Duración estimada**: 3-4 horas

### 8. **navigation-routing-base**
- **Funcionalidad**: Layout base, navbar/sidebar adaptado por rol, react-router con guards, rutas públicas/privadas, componentes de error (403, 404)
- **Historias**: US-075, US-076
- **Dependencias**: auth-frontend-interceptor
- **Razón**: El esqueleto de navegación que todas las páginas futuras necesitarán.
- **Duración estimada**: 3-4 horas

---

## Sprint 2 — Catálogo Base (2 changes)

### 9. **categories-backend**
- **Funcionalidad**: CRUD completo de categorías, jerarquía recursiva con CTE, soft delete, validación de ciclos
- **Historias**: US-007, US-008, US-009, US-010
- **Dependencias**: auth-backend
- **Razón**: Las categorías son estructura del catálogo. Los productos las necesitan.
- **Duración estimada**: 3-4 horas

### 10. **ingredients-backend**
- **Funcionalidad**: CRUD de ingredientes, campo es_alergeno, soft delete, filtrados por alérgeno
- **Historias**: US-011, US-012, US-013, US-014
- **Dependencias**: auth-backend
- **Razón**: Los ingredientes se asocian a productos. Independiente de categorías.
- **Duración estimada**: 2-3 horas

---

## Sprint 3 — Productos (2 changes)

### 11. **products-backend**
- **Funcionalidad**: CRUD de productos, asociación M2M con categorías e ingredientes, stock management, soft delete, endpoint público con filtros
- **Historias**: US-015, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023
- **Dependencias**: categories-backend, ingredients-backend
- **Razón**: El corazón del catálogo. Los clientes necesitan ver productos.
- **Duración estimada**: 5-6 horas

### 12. **products-frontend-catalog**
- **Funcionalidad**: Listado de productos (catálogo público), detalle de producto, filtros (categoría, búsqueda, rango de precio, alergenos), paginación, skeleton loaders, TanStack Query
- **Historias**: US-018, US-019, US-023
- **Dependencias**: products-backend, navigation-routing-base
- **Razón**: Los clientes necesitan ver y explorar el catálogo.
- **Duración estimada**: 4-5 horas

---

## Sprint 4 — Perfil y Direcciones (2 changes)

### 13. **user-profile**
- **Funcionalidad**: Ver perfil propio, editar datos personales, cambiar contraseña (validación de actual), invalidación de refresh tokens en cambio de password
- **Historias**: US-061, US-062, US-063
- **Dependencias**: auth-backend, navigation-routing-base
- **Razón**: Básico de cualquier usuario autenticado.
- **Duración estimada**: 2-3 horas

### 14. **delivery-addresses**
- **Funcionalidad**: CRUD de direcciones, dirección predeterminada, ownership validation, endpoint GET único del cliente, PATCH /principal
- **Historias**: US-024, US-025, US-026, US-027, US-028
- **Dependencias**: auth-backend
- **Razón**: Necesarias antes de crear pedidos. Los clientes almacenan direcciones.
- **Duración estimada**: 3-4 horas

---

## Sprint 5 — Carrito de Compras (2 changes)

### 15. **shopping-cart-zustand**
- **Funcionalidad**: Store Zustand completo (addItem, removeItem, updateQuantity, clearCart), persistencia en localStorage, personalización de ingredientes, cálculo de totales
- **Historias**: US-029, US-030, US-031, US-032, US-033, US-034
- **Dependencias**: products-backend, zustand-stores-base
- **Razón**: El carrito es 100% client-side. No hay backend para esto.
- **Duración estimada**: 2-3 horas

### 16. **checkout-validation-frontend**
- **Funcionalidad**: Validación pre-checkout (stock, disponibilidad), detección de cambios de precio, modal de confirmación, notificaciones al cliente
- **Historias**: US-069, US-070
- **Dependencias**: shopping-cart-zustand, products-backend
- **Razón**: Validar ANTES de intentar crear el pedido. Mejor UX.
- **Duración estimada**: 2-3 horas

---

## Sprint 6 — Creación de Pedidos (2 changes)

### 17. **order-creation-backend**
- **Funcionalidad**: Endpoint POST /pedidos, creación atómica con UoW, snapshots de precio y dirección, validación de stock dentro de transacción, HistorialEstadoPedido inicial, estado PENDIENTE
- **Historias**: US-035, US-036, US-037, US-038
- **Dependencias**: delivery-addresses, products-backend, database-schema-seed
- **Razón**: Core del negocio. Crear un pedido es la operación más compleja — múltiples inserts atómicos.
- **Duración estimada**: 5-6 horas

### 18. **order-creation-frontend-checkout**
- **Funcionalidad**: Componentes de checkout (selección de dirección, confirmación de items con snapshots, resumen de total), flujo post-creación, confirmación visual
- **Historias**: US-035, US-071
- **Dependencias**: order-creation-backend, checkout-validation-frontend, shopping-cart-zustand
- **Razón**: UI para que el cliente confirme y cree el pedido.
- **Duración estimada**: 3-4 horas

---

## Sprint 7 — Pagos MercadoPago (1 change)

### 19. **payment-mercadopago-integration**
- **Funcionalidad**: SDK MercadoPago.js (tokenización PCI SAQ-A), endpoint crear preferencia/orden, webhook IPN (/webhooks/mercadopago), idempotency_key UUID, transición automática PENDIENTE→CONFIRMADO, tabla Pago completa
- **Historias**: US-045, US-046, US-047, US-048
- **Dependencias**: order-creation-backend
- **Razón**: Los pedidos pasan de PENDIENTE a CONFIRMADO cuando el pago es aprobado. Sin esto, los pedidos nunca avanzan.
- **Duración estimada**: 6-7 horas (incluye configuración Sandbox y testing)

---

## Sprint 8 — Máquina de Estados (1 change)

### 20. **order-state-machine-fsm**
- **Funcionalidad**: FSM completa (PENDIENTE, CONFIRMADO, EN_PREPARACIÓN, EN_CAMINO, ENTREGADO, CANCELADO), transiciones validadas en Service, decremento de stock en CONFIRMADO, restauración en CANCELADO, HistorialEstadoPedido append-only con auditoría completa
- **Historias**: US-039, US-040, US-041, US-042, US-043, US-044
- **Dependencias**: payment-mercadopago-integration
- **Razón**: Define todo el ciclo de vida del pedido. Gestores de pedidos usarán esto para avanzar estados.
- **Duración estimada**: 5-6 horas

---

## Sprint 9 — Visualización de Pedidos (2 changes)

### 21. **order-visualization-backend**
- **Funcionalidad**: GET /pedidos (listado filtrado por usuario si es CLIENT, todos si ADMIN/PEDIDOS), GET /pedidos/{id} con snapshots y historial, paginación, filtros por estado y fecha
- **Historias**: US-049, US-050, US-051, US-052
- **Dependencias**: order-state-machine-fsm
- **Razón**: Clientes ven sus pedidos, gestores ven todos. Información read-only.
- **Duración estimada**: 3-4 horas

### 22. **order-visualization-frontend**
- **Funcionalidad**: Página "Mis Pedidos" (cliente), panel de gestión de pedidos (gestor), detalles con timeline de estados, historial, información de pago, botones para cambiar estado (solo gestor)
- **Historias**: US-049, US-050, US-051, US-052, US-072
- **Dependencias**: order-visualization-backend, navigation-routing-base
- **Razón**: UI para que clientes y gestores vean sus pedidos y cambien estados.
- **Duración estimada**: 4-5 horas

---

## Sprint 10 — Administración de Usuarios (1 change)

### 23. **admin-users-management**
- **Funcionalidad**: Panel de usuarios (GET /admin/usuarios), editar usuario (PUT), cambiar rol, desactivar (PATCH /estado), busca por email/nombre, filtro por rol, paginación, validación de no quitar último ADMIN
- **Historias**: US-053, US-054, US-055
- **Dependencias**: auth-backend, navigation-routing-base
- **Razón**: Admin necesita controlar usuarios del sistema.
- **Duración estimada**: 3-4 horas

---

## Sprint 11 — Acceso Admin Ampliado (1 change)

### 24. **admin-catalog-permissions**
- **Funcionalidad**: Extender endpoints de productos, categorías e ingredientes para aceptar tanto ADMIN como STOCK/PEDIDOS según corresponda. Admin tiene acceso completo a gestionar todo.
- **Historias**: US-064, US-065
- **Dependencias**: products-backend, order-state-machine-fsm, admin-users-management
- **Razón**: Admin necesita poder intervenir en catalogo y pedidos sin depender del gestor.
- **Duración estimada**: 1-2 horas

---

## Sprint 12 — Dashboard y Métricas (1 change)

### 25. **admin-dashboard-metrics**
- **Funcionalidad**: Panel de métricas (GET /admin/metricas/resumen), gráfico de ventas por periodo, top productos más vendidos, distribución por estado, filtro por fecha, recharts en frontend
- **Historias**: US-056, US-057, US-058, US-059
- **Dependencias**: order-creation-backend (datos)
- **Razón**: Admin ve inteligencia del negocio. Prioridad media pero completa la experiencia admin.
- **Duración estimada**: 4-5 horas

---

## Sprint 13 (Futuro) — Configuración del Sistema

### 26. **system-configuration** *(Baja prioridad — postergable)*
- **Funcionalidad**: Panel de configuración global (horarios, zona de entrega, parámetros), tabla key-value en BD
- **Historias**: US-060
- **Dependencias**: auth-backend
- **Razón**: Baja prioridad. Se puede implementar en fase posterior.
- **Duración estimada**: 2-3 horas

---

## Grafo de Dependencias

```
setup-backend-core
├─ database-schema-seed
├─ backend-error-handling-validation
└─ zustand-stores-base ← setup-frontend-core
   
auth-backend (depende: database-schema-seed, backend-error-handling-validation)
└─ auth-frontend-interceptor (depende: zustand-stores-base)
   └─ navigation-routing-base

categories-backend (depende: auth-backend)
├─ products-backend
│  ├─ products-frontend-catalog
│  ├─ order-creation-backend
│  └─ checkout-validation-frontend
│
ingredients-backend (depende: auth-backend)
└─ products-backend

user-profile (depende: auth-backend, navigation-routing-base)

delivery-addresses (depende: auth-backend)
└─ order-creation-backend

shopping-cart-zustand (depende: products-backend)
└─ checkout-validation-frontend
   └─ order-creation-frontend-checkout
      └─ order-creation-backend

order-creation-backend
└─ payment-mercadopago-integration
   └─ order-state-machine-fsm
      ├─ order-visualization-backend
      │  └─ order-visualization-frontend
      │
      └─ admin-catalog-permissions

admin-users-management

admin-dashboard-metrics (depende: order-creation-backend)
```

---

## Resumen por Sprint

| Sprint | Changes | Duración | Objetivo |
|--------|---------|----------|----------|
| **0** | setup-backend-core, setup-frontend-core, database-schema-seed, backend-error-handling-validation, zustand-stores-base | 12-16h | Infraestructura base |
| **1** | auth-backend, auth-frontend-interceptor, navigation-routing-base | 11-14h | Autenticación y navegación |
| **2** | categories-backend, ingredients-backend | 5-7h | Catálogo base |
| **3** | products-backend, products-frontend-catalog | 9-11h | Productos |
| **4** | user-profile, delivery-addresses | 5-7h | Perfil y direcciones |
| **5** | shopping-cart-zustand, checkout-validation-frontend | 4-6h | Carrito |
| **6** | order-creation-backend, order-creation-frontend-checkout | 8-10h | Creación de pedidos |
| **7** | payment-mercadopago-integration | 6-7h | Pagos MercadoPago |
| **8** | order-state-machine-fsm | 5-6h | FSM completa |
| **9** | order-visualization-backend, order-visualization-frontend | 7-9h | Visualización de pedidos |
| **10** | admin-users-management | 3-4h | Admin usuarios |
| **11** | admin-catalog-permissions | 1-2h | Permisos admin ampliados |
| **12** | admin-dashboard-metrics | 4-5h | Dashboard y métricas |

**Total estimado**: 80-110 horas

---

## Convenciones del Proyecto

- **Package manager**: `pnpm` para todo el frontend (NO npm ni yarn). Todos los comandos en specs, tasks y documentación deben usar `pnpm`.
- **Backend**: Python con `pip` y `requirements.txt`.

## Reglas Importantes

- **Nunca implementes sin artefactos**: Si no existe `proposal.md` y `design.md` aprobados, no hay `/opsx:apply`.
- **El orden importa**: Si el change B necesita código del change A, A debe estar archivado antes.
- **Un change = un commit** (o varios commits atómicos). Nunca mezcles dos changes.
- **Las specs son código**: Se versionan en git, se revisan en PRs, evolucionan con el proyecto.

---

## Próximos Pasos

1. Revisá este mapa y discutí si hay cambios
2. Una vez aprobado, comenzamos con: `/opsx:propose setup-backend-core`
3. Cada change genera proposal.md, design.md y tasks.md
4. Se revisan los artefactos antes de implementar
5. Se ejecuta `/opsx:apply [nombre]` cuando esté aprobado
6. Se ejecuta `/opsx:archive [nombre]` cuando esté completado

¡Adelante! 🚀
