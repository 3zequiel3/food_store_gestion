# addresses — Módulo de Direcciones de Entrega

Gestión de direcciones de entrega para clientes autenticados. Cubre US-024 a US-028.

## Endpoints (montados bajo `/api/v1/direcciones`)

| Método | Path | Propósito |
|--------|------|-----------|
| `POST` | `/` | Crear dirección; auto-marca `es_principal=True` si es la primera (RN-DI01) |
| `GET` | `/` | Listar direcciones activas propias (principal primero) |
| `PUT` | `/{address_id}` | Actualización parcial (semántica PATCH via `exclude_unset`) |
| `DELETE` | `/{address_id}` | Soft delete; borrar la principal deja al usuario sin predeterminada (D5) |
| `PATCH` | `/{address_id}/predeterminada` | Swap atómico: la seleccionada queda principal (RN-DI02) |

## Reglas de negocio clave

- **RN-DI01**: primera dirección → `es_principal=True` automáticamente.
- **RN-DI02**: solo una dirección puede ser predeterminada por usuario; el PATCH hace swap atómico.
- **D6 (anti-leak)**: dirección inexistente o ajena → **404**, no 403.
- **Anti-smuggling**: `es_principal` y `usuario_id` son campos prohibidos en POST/PUT (`extra="forbid"`).

## Ejemplo curl

```bash
curl -X POST https://api.example.com/api/v1/direcciones \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "calle": "Av Siempre Viva",
    "numero": "742",
    "piso_depto": "3 B",
    "ciudad": "Springfield",
    "codigo_postal": "1000",
    "referencia": "frente al parque"
  }'
```

## Migración pendiente

Antes de arrancar el backend, correr `alembic upgrade head` para agregar la columna `piso_depto` (migración `piso_depto_delivery_addresses`).
