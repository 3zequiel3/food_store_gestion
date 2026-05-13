# Products module

Implements the product catalog for Food Store: CRUD, availability/stock patches, and M:N associations with categories and ingredients.

## Endpoints (prefix: `/api/v1/productos`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/` | ADMIN / STOCK | Create product (optionally with `categoria_ids`) |
| `GET` | `/` | public | List paginated (filters: `categoria_id`, `search`, `disponible`, `excluir_alergenos`) |
| `GET` | `/{id}` | public | Product detail with categories and ingredients |
| `PUT` | `/{id}` | ADMIN / STOCK | Partial update (exclude_unset) |
| `DELETE` | `/{id}` | ADMIN / STOCK | Soft delete |
| `PATCH` | `/{id}/disponibilidad` | ADMIN / STOCK | Toggle availability |
| `PATCH` | `/{id}/stock` | ADMIN / STOCK | Set absolute stock |
| `PUT` | `/{id}/categorias` | ADMIN / STOCK | Replace full category set (bulk) |
| `GET` | `/{id}/ingredientes` | public | List ingredient associations with `es_removible` flag |
| `POST` | `/{id}/ingredientes` | ADMIN / STOCK | Add ingredient association |
| `DELETE` | `/{id}/ingredientes/{ing_id}` | ADMIN / STOCK | Remove ingredient association (soft delete on pivot) |

## Architecture

- **Pattern**: `Router → Service → UoW → Repository → Model`. Router owns `uow.commit()`; service never commits.
- **Catalog filter** (`list_paginated_with_filters`): 4 combinable filters using `LOWER + LIKE` (SQLite-compatible, not `ILIKE`). Allergen exclusion uses `NOT EXISTS` subquery.
- **M:N pivot reactivation**: soft-deleted pivot rows (both `product_categories` and `product_ingredients`) are reactivated on re-association instead of duplicated.
- **Migration**: `20260508_0001_es_removible_to_product_ingredients.py` adds `es_removible BOOLEAN NOT NULL DEFAULT false` to `product_ingredients`.

## Example requests

```bash
# Create a product with categories
curl -X POST http://localhost:8000/api/v1/productos \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Pizza Margherita", "precio": "12.50", "stock_cantidad": 30, "categoria_ids": [1, 2]}'

# List with combined filters
curl "http://localhost:8000/api/v1/productos?search=pizza&categoria_id=1&disponible=true&excluir_alergenos=true&page=1&limit=10"
```
