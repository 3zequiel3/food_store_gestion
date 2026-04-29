# Food Store

E-commerce de productos alimenticios. TPI full-stack con **React + TypeScript** (Vite) y **FastAPI + SQLModel + PostgreSQL**, integrado a **MercadoPago**. Metodología Spec-Driven Development, organización feature-first.

**Especificación canónica** (leer antes de tocar código):
- `Integrador.txt` — spec técnica v5, ERD, diagramas, módulos.
- `Descripcion.txt` — descripción narrativa, arquitectura, patrones, rúbrica.
- `Historias_de_usuario.txt` — historias US-*, reglas de negocio RN-*.

Si una instrucción de este archivo entra en conflicto con los `.txt`, **gana la spec**. Este archivo es un resumen operativo, no la fuente de verdad.

> Este archivo aplica a **cualquier agente** trabajando en el repo (Copilot, Cursor, OpenCode, Codex, Claude Code). Reglas Claude-específicas viven en `CLAUDE.md`.

---

## Estructura del repo

```
trabajo_food_store/
├── docs/
│   ├── CHANGES.md              ← ROADMAP: mapa de los 25 changes en orden, con dependencias
│   ├── Integrador.txt          ← spec técnica v5 (ERD, módulos, diagramas)
│   ├── Descripcion.txt         ← arquitectura, patrones, rúbrica
│   └── Historias_de_usuario.txt ← US-* y RN-*
├── openspec/
│   ├── changes/                ← changes activos (uno por feature)
│   │   ├── archive/            ← changes ya completados
│   │   └── <change-name>/      ← proposal.md, design.md, tasks.md, specs/
│   └── specs/                  ← specs vigentes por capacidad
│       ├── backend-setup/
│       ├── base-entities/
│       └── logging-audit/
├── backend/
│   ├── main.py, config.py, dependencies.py, logging_config.py
│   ├── features/               ← módulos funcionales (feature-first)
│   │   ├── auth/  orders/  payments/  products/  users/
│   ├── shared/                 ← infraestructura común
│   │   ├── enums.py models.py repository.py service.py unit_of_work.py
│   ├── migrations/             ← Alembic
│   └── tests/                  ← unit/ integration/
├── frontend/
│   └── src/                    ← Feature-Sliced Design
│       ├── app/                ← providers, routing, layout raíz
│       ├── pages/              ← rutas top-level
│       ├── widgets/            ← composiciones de features
│       ├── features/           ← unidades funcionales (auth, cart, etc.)
│       ├── entities/           ← modelos de dominio (User, Product, Order)
│       └── shared/             ← UI kit, utils, api client, hooks
├── .mcp.json                   ← MCPs para Claude Code
├── .vscode/mcp.json            ← MCPs para VS Code + Copilot
└── opencode.json               ← MCPs + permisos para OpenCode
```

**Dónde mirar primero:**
- ¿Qué hay que hacer? → `docs/CHANGES.md` (roadmap completo)
- ¿Cómo funciona el dominio? → `docs/Integrador.txt` + `docs/Historias_de_usuario.txt`
- ¿Qué changes están en curso? → `openspec/changes/` (no `archive/`)
- ¿Qué reglas de capacidad ya están vigentes? → `openspec/specs/`

---

## Setup

```bash
# Backend
cd backend/
{activacion de entorno virtual}
cp .env.example .env             # completar secrets
pip install -r requirements.txt

# Database setup (requiere PostgreSQL corriendo)
createdb foodstore_dev
export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/foodstore_dev
cd backend && python -m alembic upgrade head   # crea las 16 tablas
python -m backend.scripts.seed                  # carga roles, estados, formas de pago, admin
cd ..

uvicorn backend.main:app --reload    # http://localhost:8000/docs

# Frontend
cd frontend/
cp .env.example .env
pnpm install
pnpm dev                         # http://localhost:5173
```

### Database setup detallado

**Requisitos**: PostgreSQL 14+ corriendo localmente.

```bash
# 1. Crear base de datos de desarrollo
createdb foodstore_dev

# 2. Exportar variable de entorno (o setear en .env)
export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/foodstore_dev

# 3. Correr migración inicial (desde el directorio backend/)
cd backend
python -m alembic upgrade head
# Verifica: psql foodstore_dev -c '\dt'
# Debe listar 16 tablas + alembic_version

# 4. Cargar datos semilla
python -m backend.scripts.seed
# Carga: 4 roles (ADMIN/STOCK/PEDIDOS/CLIENT)
#        6 estados de pedido (PENDIENTE..CANCELADO)
#        3 formas de pago (MERCADOPAGO/EFECTIVO/TRANSFERENCIA)
#        1 usuario admin (admin@foodstore.local)
# El seed es idempotente — re-ejecutar no genera duplicados

# 5. (Opcional) Verificar datos semilla
psql foodstore_dev -c 'SELECT id, codigo FROM roles ORDER BY id;'
# → 4 filas: 1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT

# 6. Ciclo de downgrade/upgrade para verificar idempotencia de migración
python -m alembic downgrade base && python -m alembic upgrade head
```

**Nota sobre ADMIN_PASSWORD**: si no se setea la variable de entorno `ADMIN_PASSWORD`, el seed usa el default `admin1234` y emite un WARNING visible en stderr. En producción SIEMPRE setear `ADMIN_PASSWORD` antes de correr el seed.

**NO hay auto-migrate**: el app FastAPI NO ejecuta `alembic upgrade head` automáticamente al arrancar. Las migraciones se corren manualmente o vía CI.

MercadoPago en Sandbox: usar credenciales con prefijo `TEST-`.

---

## Reglas arquitectónicas (inviolables)

**Backend — flujo de imports unidireccional**:
```
Router → Service → UoW → Repository → Model
```
Ninguna capa importa de una superior. Un Model nunca importa de un Service. Un Router no contiene lógica de negocio, solo delega. `commit()`/`rollback()` es responsabilidad exclusiva del UoW — un Service que commitea está mal.

**Frontend — Feature-Sliced Design**:
```
app → pages → widgets → features → entities → shared
```
Cada capa solo importa de inferiores. Features no importan entre sí.

**Separación de estado (frontend)**:
- **Zustand** = estado del **cliente** (carrito, auth, UI local, flujo de pago).
- **TanStack Query** = estado del **servidor** (productos, pedidos, dashboard).
- Mezclarlos en un mismo store es un bug arquitectónico, no una decisión.

**Patrones críticos que deben estar implementados de verdad** (no solo nombrados):
- **Snapshot** de `precio` y `direccion` en pedidos → inmutables tras creación.
- **Audit Trail append-only** en `HistorialEstadoPedido` → jamás UPDATE ni DELETE.
- **FSM** del pedido → transiciones inválidas devuelven error, nunca mutan silenciosamente.
- **Unit of Work** → creación de pedido es atómica (todo o nada).
- **Idempotencia** en webhooks de pago → duplicados se descartan por `idempotency_key`.

---

## Code style

- **Precios**: `DECIMAL(10,2)` / `NUMERIC` en BD, nunca `float`.
- **Stock**: entero ≥ 0 con `CHECK` en BD.
- **Passwords**: bcrypt cost ≥ 12. Jamás plaintext, jamás en logs.
- **Refresh tokens**: se persiste el SHA-256, no el token crudo.
- **Errores HTTP**: RFC 7807 (`type`, `title`, `status`, `detail`, `instance`).
- **Login**: no diferenciar "email no existe" de "password inválida" (RN-AU08).
- **PCI**: datos de tarjeta se tokenizan en el navegador con el SDK de MercadoPago, jamás llegan al backend.
- **Soft delete**: todas las entidades principales heredan `BaseModel` que incluye `eliminado_en: DateTime(timezone=True) nullable`. Repositorios DEBEN filtrar `WHERE eliminado_en IS NULL` por defecto en todos los métodos `query()`, `get()`, `list()`. Para auditoría/admin implementar `query_with_deleted()` separado. NUNCA hacer hard DELETE en tablas con `eliminado_en` — setear `eliminado_en = now()`.
- **Append-only**: `HistorialEstadoPedido` hereda `AppendOnlyBaseModel` (solo `id` + `creado_en`, sin `actualizado_en` ni `eliminado_en`). Repositorios de historial son INSERT + SELECT únicamente, nunca UPDATE ni DELETE.
- **Paginación**: `skip` + `limit` con metadata de total en la respuesta.

Lo que no está acá lo resuelve el linter/formatter — no documentamos indentación ni comas finales.

---

## Testing

- Tests unitarios de Services con mocks del UoW (no tocan HTTP ni BD).
- Tests de integración para el flujo completo de pedido + FSM + snapshot.
- Tests del flujo de auth (login, refresh, rotación, rate limit).
- Tests de idempotencia de webhooks de pago.

Correr antes de abrir PR: `pytest` en backend, `pnpm test` en frontend, `pnpm lint` + `pnpm typecheck`.

---

## MCPs configurados

Los archivos de config están versionados en el repo y se activan al clonar. Secrets vía `.env` (nunca en el JSON).

### `github` (remoto, OAuth por usuario)
Para PRs, issues, revisión de código, logs de Actions, alertas de Dependabot.
URL: `https://api.githubcopilot.com/mcp/` — cada dev hace OAuth con su cuenta al primer uso.

### `postgres` (Postgres MCP Pro de crystaldba)
Para inspeccionar esquema, validar queries, verificar seed data. **Siempre apuntado a la BD de desarrollo con un usuario read-only**, nunca a producción con write.
Imagen Docker: `crystaldba/postgres-mcp --access-mode=restricted` (read-only a nivel servidor además del usuario de BD).
> ⚠️ NO usar `@modelcontextprotocol/server-postgres` (deprecado julio 2025, vulnerable a SQL injection que bypassea el read-only).

### `context7` (remoto, API key free)
Documentación actualizada de FastAPI, SQLModel, TanStack Query, Zustand, recharts, MercadoPago SDK. Evita que el agente alucine APIs viejas.
URL: `https://mcp.context7.com/mcp` — requiere `CONTEXT7_API_KEY` (gratis en context7.com).

### Archivos de config por cliente

- **Claude Code**: `.mcp.json` en la raíz
- **VS Code + Copilot**: `.vscode/mcp.json` (clave raíz `"servers"`, no `"mcpServers"`)
- **OpenCode**: `opencode.json` en la raíz con bloque `mcp` y permisos (`github: ask`, `postgres: ask`, `context7: allow`)

Los tres se commitean. Los secrets (`DATABASE_URL_DEV_READONLY`, `CONTEXT7_API_KEY`) se resuelven por variable de entorno.

---

## Commits — Conventional Commits (obligatorio)

Formato: `<type>(<scope>): <subject>`

**Reglas duras:**
- Sin `Co-Authored-By` ni atribución a IA. **Nunca.**
- Subject en minúsculas, imperativo, sin punto final, ≤ 72 caracteres.
- Commits pequeños e incrementales. La rúbrica penaliza repos con un solo commit masivo.
- Body opcional para el "por qué" (no el "qué"); footer opcional para refs (`Closes US-042`, `Refs RN-PE03`).
- Breaking change: agregar `!` después del scope (`feat(auth)!: rotar refresh token`) o footer `BREAKING CHANGE: ...`.

**Types permitidos:**

| Type | Cuándo |
|------|--------|
| `feat` | Nueva funcionalidad de usuario (US-*). |
| `fix` | Corrección de bug (incluir RN-* o issue si aplica). |
| `chore` | Tareas de mantenimiento, deps, tooling, configs (no afectan código de producción). |
| `docs` | Solo cambios en documentación (`README`, `CLAUDE.md`, `AGENTS.md`, `docs/*.md`, comentarios). |
| `refactor` | Cambio de código que no agrega features ni corrige bugs (reorganizar, renombrar, extraer). |
| `test` | Agregar o corregir tests, sin cambio en código de producción. |
| `perf` | Mejora de performance medible. |
| `style` | Formato, espacios, comas — sin cambio de lógica. |
| `build` | Cambios al sistema de build (Vite, pip, Alembic config, Dockerfile). |
| `ci` | Cambios a CI/CD (`.github/workflows/*`). |
| `revert` | Revertir un commit previo. |

**Scopes sugeridos** (no exhaustivos):

- Backend: `auth`, `users`, `products`, `orders`, `payments`, `shared`, `db`, `migrations`, `tests`
- Frontend: `auth-ui`, `cart`, `checkout`, `dashboard`, `routing`, `stores`, `shared-ui`
- Cross: `agents` (CLAUDE/AGENTS.md), `docs`, `mcp`, `openspec`, `deps`

**Ejemplos:**

```
feat(auth): implementar rotación de refresh token
fix(orders): rechazar transición EN_CAMINO→PENDIENTE en FSM
chore(deps): bump fastapi a 0.115.0
docs(agents): separar CLAUDE.md y AGENTS.md por audiencia
refactor(shared): extraer BaseRepository del UoW
test(payments): cubrir idempotencia de webhook duplicado
build(frontend): migrar a vite 5
ci: agregar workflow de typecheck en PR
```

---

## PR instructions

- Rama: `<type>/<scope>-<resumen-corto>` (ej. `feat/auth-refresh-rotation`, `fix/orders-fsm-validation`).
- Antes de abrir PR: lint + typecheck + tests verdes.
- Título del PR: mismo formato de commit (`<type>(<scope>): <subject>`).
- Descripción: qué RN o US cubre (ej. "Implementa RN-PE03 y cierra US-042").
- No commitear `.env`, tokens de MP, hashes de password, ni snapshots de BD.

---

## Anti-patterns (si el agente hace esto, está mal)

- Importar hacia arriba (Service importando Router, Repository importando Service, etc.).
- Lógica de negocio en un Router.
- `commit()` o `rollback()` dentro de un Service.
- FK viva de precio/dirección en un pedido en vez de snapshot.
- UPDATE o DELETE sobre `HistorialEstadoPedido`.
- `float` para dinero.
- Token de acceso o password en `localStorage`.
- Estado del servidor dentro de un store Zustand (o viceversa).
- Usar `@modelcontextprotocol/server-postgres` (deprecado/inseguro).
- Commit con `.env` adentro.
- Saltar la FSM para cambiar el estado de un pedido.
