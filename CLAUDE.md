# AGENTS.md — Food Store

E-commerce de productos alimenticios. TPI full-stack con **React + TypeScript** (Vite) y **FastAPI + SQLModel + PostgreSQL**, integrado a **MercadoPago**. Metodología Spec-Driven Development, organización feature-first.

**Especificación canónica** (leer antes de tocar código):
- `Integrador.txt` — spec técnica v5, ERD, diagramas, módulos.
- `Descripcion.txt` — descripción narrativa, arquitectura, patrones, rúbrica.
- `Historias_de_usuario.txt` — historias US-*, reglas de negocio RN-*.

Si una instrucción de este archivo entra en conflicto con los `.txt`, **gana la spec**. Este archivo es un resumen operativo, no la fuente de verdad.

---

## Setup

```bash
# Backend
cd backend/
{activacion de entorno virtual}
cp .env.example .env          # completar secrets
pip install -r requirements.txt  # o pip install -r requirements.txt
alembic upgrade head          # crear tablas
python -m app.seed            # roles, estados, formas de pago, admin
uvicorn app.main:app --reload # http://localhost:8000/docs

# Frontend
cd frontend/
cp .env.example .env
pnpm install
pnpm dev                      # http://localhost:5173
```

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
- **Soft delete**: todas las entidades principales usan `eliminado_en` / `deleted_at` nullable.
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

## Skills — cuándo activar cada una

El agente debe invocar la skill correspondiente **antes** de producir output, según el tipo de tarea. Cómo se carga la skill depende del cliente (Claude Code, Copilot, OpenCode, Cursor); acá solo se lista el nombre y el disparador.

| Skill | Activar cuando la tarea es… |
|---|---|
| `frontend-design` | Crear o modificar componentes React, páginas, layouts, estilos Tailwind, el dashboard con recharts, formularios con TanStack Form, o cualquier decisión visual/UX. |
| `web-artifacts-builder` | Prototipar un componente o pantalla **en el chat** (mockup rápido, demo) antes de llevarlo al repo. |
| `mcp-builder` | Construir un MCP server custom (por ejemplo, exponer la API interna de Food Store como MCP para consumirla desde otra sesión). |
| `skill-creator` | Crear una skill específica del proyecto (por ejemplo, una skill que cargue automáticamente las RN-* cuando el agente toque lógica de negocio). |
| `pdf-reading` | La cátedra sube una rúbrica o consigna en PDF y hay que extraer info. |

**Backend Python (FastAPI / SQLModel / Alembic)**: no hay skill dedicada. La regla es: (1) consultar `context7` MCP para la doc actual de la librería involucrada, (2) respetar la regla de oro de imports, (3) envolver toda operación multi-tabla en el UoW.

---

## MCPs configurados

Los tres archivos de config están versionados en el repo y se activan al clonar. Secrets vía `.env` (nunca en el JSON).

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

### Archivos de config

- Claude Code: `.mcp.json` en la raíz
- VS Code + Copilot: `.vscode/mcp.json` (clave raíz `"servers"`, no `"mcpServers"`)
- OpenCode: `opencode.json` en la raíz con bloque `mcp` y permisos (`github: ask`, `postgres: ask`, `context7: allow`)

Los tres se commitean. Los secrets (`DATABASE_URL_DEV_READONLY`, `CONTEXT7_API_KEY`) se resuelven por variable de entorno.

---

## PR instructions

- Rama: `feat/<modulo>-<resumen>` o `fix/<modulo>-<resumen>`.
- Commits pequeños e incrementales (la rúbrica penaliza repos con un solo commit masivo).
- Antes de abrir PR: lint + typecheck + tests verdes.
- Título: `<modulo>: <qué hace>` (ej. `pedidos: FSM rechaza transición EN_CAMINO→PENDIENTE`).
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

---
