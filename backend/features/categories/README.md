# categories — Catálogo jerárquico

Módulo CRUD de categorías de productos con jerarquía recursiva (CTE PostgreSQL).
Cubre US-007 a US-010.

## Endpoints

| Método | Path | Auth |
|--------|------|------|
| POST | `/api/v1/categorias` | ADMIN, STOCK |
| GET | `/api/v1/categorias` | público (árbol completo) |
| PUT | `/api/v1/categorias/{id}` | ADMIN, STOCK |
| DELETE | `/api/v1/categorias/{id}` | ADMIN, STOCK (soft delete) |

## Patrón

Router → Service → UoW → Repository → Model. El service NO hace `uow.commit()`;
el router es dueño de la frontera transaccional (D6 en design.md).

El árbol se construye con una CTE recursiva en `CategoryRepository.get_tree_cte()`.
El modelo `Categoria` vive en `backend.features.catalog.models` (no se duplica aquí).

## Curl ejemplo

```bash
# Crear categoría raíz (requiere sesión ADMIN o STOCK en cookies.txt)
curl -X POST http://localhost:8000/api/v1/categorias \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Bebidas"}'

# Crear subcategoría
curl -X POST http://localhost:8000/api/v1/categorias \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Gaseosas", "padre_id": 1}'

# Obtener árbol completo (sin auth)
curl http://localhost:8000/api/v1/categorias
```
