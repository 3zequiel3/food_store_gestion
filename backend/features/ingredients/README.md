# Ingredients module

CRUD plano para ingredientes del catálogo. Cubre US-011, US-012, US-013, US-014 y RN-CA07/RN-CA09.

## Endpoints

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/ingredientes` | ADMIN, STOCK | Crear ingrediente |
| `GET` | `/api/v1/ingredientes` | Público | Listar paginado, filtro `?es_alergeno=true\|false` |
| `GET` | `/api/v1/ingredientes/{id}` | Público | Obtener por id |
| `PUT` | `/api/v1/ingredientes/{id}` | ADMIN, STOCK | Actualizar parcial (exclude_unset) |
| `DELETE` | `/api/v1/ingredientes/{id}` | ADMIN, STOCK | Soft delete (sin guards) |

## Notas clave

- El modelo `Ingrediente` se importa desde `backend.features.catalog.models` — no hay `models.py` en este módulo.
- El service usa `model_dump(exclude_unset=True)` en update para preservar `es_alergeno` cuando solo se envía `nombre`.
- `find_by_nombre` no filtra por `eliminado_en` — el constraint UNIQUE de la DB es table-wide.
- Soft delete vía `BaseRepository.delete()` (sets `eliminado_en`). Hard delete nunca ocurre.
- UoW via `Depends(get_uow)`; el commit es responsabilidad del router (D6 en design.md).

## Ejemplos rápidos

```bash
# Crear ingrediente alérgeno
curl -X POST http://localhost:8000/api/v1/ingredientes \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Mani", "es_alergeno": true}'

# Listar solo alérgenos, segunda página
curl "http://localhost:8000/api/v1/ingredientes?es_alergeno=true&page=1&limit=20"
```
