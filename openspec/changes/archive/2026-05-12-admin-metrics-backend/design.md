# Design: admin-metrics-backend

## Módulo: `backend/features/admin_metrics/`

### Archivos a crear

```
backend/features/admin_metrics/
├── __init__.py
├── repository.py   — queries SQLAlchemy 2.0 (select())
├── schemas.py      — Pydantic response models (Decimal como str)
├── service.py      — orchestration + date-grouping en Python
└── router.py       — 4 endpoints, require_role("ADMIN")

tests/features/admin_metrics/
├── __init__.py
└── test_admin_metrics.py
```

### Decisiones de diseño

#### D1 — Sin UoW propio (solo lectura)
Las métricas son READ-ONLY. No hay writes, no hay transacciones de negocio. El service abre sesión via `get_session_factory()()` directamente — no necesita UoW. Alternativa considerada: UoW sin commit — innecesariamente complejo para queries SELECT.

#### D2 — Agrupación por periodo en Python, no en DB
`DATE_TRUNC` (PostgreSQL) y `EXTRACT` con epoch no funcionan en SQLite. Para compatibilidad con tests in-memory se traen las filas con `creado_en` y se agrupan en Python con `datetime.strftime`. En producción con Postgres esto es aceptable dado el volumen esperado (food store local, no big data).

#### D3 — Decimal como str en respuesta JSON
Pydantic v2 con `model_config = ConfigDict(json_encoders={Decimal: str})` — garantiza que ningún valor monetario pierda precisión al serializar.

#### D4 — Filtros opcionales desde/hasta como query params
`desde: Optional[date] = None`, `hasta: Optional[date] = None`. Si ambos son None, devuelve todo el histórico. El repository convierte `date` a `datetime` con `time.min` / `time.max` para hacer el WHERE sobre `creado_en` (TIMESTAMPTZ).

#### D5 — Granularidad como Enum
```python
class Granularidad(str, Enum):
    dia = "dia"
    semana = "semana"
    mes = "mes"
```
Default: `dia`. La agrupación ocurre en el service post-fetch.

#### D6 — top-productos: top N configurable, default 10, max 50
Query en repository, ordenado por `SUM(cantidad) DESC`, limit en la query SQL.

#### D7 — No hay modelos ORM nuevos
Solo se usan `Pedido`, `DetallePedido`, `Usuario`. Sin nuevas tablas.

### Endpoints

| Método | Path | Auth | Query params |
|--------|------|------|-------------|
| GET | `/api/v1/admin/metricas/resumen` | ADMIN | `desde`, `hasta` |
| GET | `/api/v1/admin/metricas/ventas-por-periodo` | ADMIN | `desde`, `hasta`, `granularidad` |
| GET | `/api/v1/admin/metricas/top-productos` | ADMIN | `desde`, `hasta`, `top` |
| GET | `/api/v1/admin/metricas/pedidos-por-estado` | ADMIN | `desde`, `hasta` |

### Response schemas

```python
# Resumen
class ResumenMetricas(BaseModel):
    total_ventas: str          # Decimal como str
    total_pedidos: int
    ticket_promedio: str       # Decimal como str
    total_usuarios: int
    periodo_desde: Optional[date]
    periodo_hasta: Optional[date]

# Ventas por periodo
class PuntoPeriodo(BaseModel):
    periodo: str               # "2026-05-01" / "2026-W18" / "2026-05"
    total_ventas: str
    cantidad_pedidos: int

class VentasPorPeriodoResponse(BaseModel):
    granularidad: str
    puntos: list[PuntoPeriodo]

# Top productos
class ProductoTop(BaseModel):
    producto_id: int
    nombre: str
    cantidad_total: int
    ingreso_total: str

class TopProductosResponse(BaseModel):
    top: int
    productos: list[ProductoTop]

# Pedidos por estado
class DistribucionEstado(BaseModel):
    estado_codigo: str
    cantidad: int

class PedidosPorEstadoResponse(BaseModel):
    distribucion: list[DistribucionEstado]
```

### Registro en main.py

```python
from backend.features.admin_metrics.router import router as admin_metrics_router
app.include_router(admin_metrics_router, prefix="/api/v1/admin/metricas", tags=["admin-metrics"])
```
