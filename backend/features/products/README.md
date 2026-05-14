# Products module

Implements the product catalog for Food Store: CRUD, availability/stock patches, and M:N associations with categories and ingredients.

## Endpoints (prefix: `/api/v1/productos`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/` | ADMIN / STOCK | Create product (optionally with `categoria_ids`) |
| `GET` | `/` | public | List paginated (filters: `categoria_id`, `search`, `disponible`, `excluir_alergenos`) |
| `GET` | `/{id}` | public | Product detail with categories and ingredients |
| `POST` | `/{id}/imagen` | ADMIN / STOCK | Upload product image using configured storage |
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

## Product image storage

`POST /api/v1/productos/{id}/imagen` accepts multipart field `file` and updates `imagen_url`.

Storage is selected by env var:

- `STORAGE=local`: saves under `backend/uploads/productos/{id}/` and serves files from `/uploads/...`.
- `STORAGE=s3`: uploads to the configured S3-compatible bucket and, by default, serves images through the backend proxy `/api/v1/productos/imagenes/...` because Railway buckets are private.


For Railway production, set `STORAGE_PUBLIC_BASE_URL` to the public backend URL, for example:

```env
STORAGE_PUBLIC_BASE_URL=https://foodstoregestion-production.up.railway.app
```

Railway S3-compatible env names:

```env
STORAGE=s3
S3_ENDPOINT_URL=https://t3.storageapi.dev
S3_REGION=auto
S3_BUCKET_NAME=your-bucket
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
```

Do not commit real S3 credentials. Configure them only in Railway variables.
