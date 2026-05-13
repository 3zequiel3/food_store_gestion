## Why

El cliente puede completar su perfil (#22 archivado) pero no tiene UI para gestionar sus direcciones de entrega. Sin direcciones, el checkout (#26) queda bloqueado. El backend de direcciones está completo desde Sprint 4 — solo falta la UI que lo consuma.

## What Changes

- Reemplazar el `PlaceholderPage` de `/cliente/direcciones` con `AddressesPage` real.
- Listado de direcciones: la principal marcada con badge, ordenada primero (igual que el backend).
- Botón "Agregar dirección" → modal con formulario de alta (TanStack Form + Zod).
- Cada tarjeta de dirección tiene: editar (abre modal pre-cargado), eliminar (con confirmación inline), y "Establecer como predeterminada" si no lo es ya.
- Nuevo módulo `features/delivery-addresses/` con types, service, schemas, hooks y components.
- Cinco endpoints consumidos: GET, POST, PUT /{id}, DELETE /{id}, PATCH /{id}/predeterminada.

## Capabilities

### New Capabilities
- `delivery-addresses-frontend`: UI cliente para ABM de direcciones de entrega.

### Modified Capabilities
<!-- ninguna spec de backend cambia -->

## Impact

- **Archivos nuevos**: `features/delivery-addresses/` completo + `pages/client/AddressesPage.tsx`.
- **Archivos modificados**: `router/AppRoute.tsx` (reemplazar PlaceholderPage en `/cliente/direcciones`).
- **Sin cambios de backend**: todos los endpoints ya existen y están testeados.
- **Dependencias externas**: ninguna nueva.
