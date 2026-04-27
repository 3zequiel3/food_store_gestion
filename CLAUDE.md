# Food Store — Claude Code

Reglas específicas de Claude Code para este proyecto.

> **Reglas generales del proyecto** (estructura del repo, arquitectura, code style, testing, MCPs, PR, anti-patterns, setup) → `.agents/AGENTS.md`. Aplica a cualquier agente.
>
> Acá solo lo Claude-específico: spec, OPSX flow, skills, modelos por fase.

---

## Spec canónica (leer ANTES de tocar código)

- `docs/Integrador.txt` — spec técnica v5 (ERD, módulos, diagramas).
- `docs/Descripcion.txt` — arquitectura, patrones, rúbrica.
- `docs/Historias_de_usuario.txt` — historias US-* y reglas de negocio RN-*.

Si una instrucción de los `.md` entra en conflicto con los `.txt`, **gana la spec**.

---

## Roadmap y changes

- **Roadmap completo**: `docs/CHANGES.md` — define los **25 changes** en orden, con dependencias y duración estimada.
- **Changes activos**: `openspec/changes/<nombre>/` (con `proposal.md`, `design.md`, `tasks.md`, `specs/`).
- **Changes archivados**: `openspec/changes/archive/YYYY-MM-DD-<nombre>/`.
- **Specs vigentes**: `openspec/specs/<capability>/spec.md` (lo que ya está aprobado y vivo).

**Antes de proponer cualquier change**: chequear `docs/CHANGES.md` para ver el orden y dependencias. No saltar dependencias — si el next-up es `auth-backend`, no arrancar con `products-backend`.

---

## Flujo OPSX (OBLIGATORIO para todo cambio sustantivo)

Todo trabajo nuevo se canaliza por OPSX. **No hay implementación libre fuera de un change.**

```
/opsx:explore  →  /opsx:propose  →  /opsx:apply  →  /opsx:archive
   (opcional)      (crear change)    (implementar)   (cerrar)
```

| Comando | Cuándo | Qué hace |
|---------|--------|----------|
| `/opsx:explore [tema]` | Cuando hay duda de enfoque, tradeoffs, o el alcance no está claro | Investigación previa, sin escribir código |
| `/opsx:propose <nombre>` | Para arrancar un change formal | Crea `openspec/changes/<nombre>/` con proposal + design + tasks + specs delta |
| `/opsx:apply <nombre>` | Para implementar las tasks del change | Escribe código real, va tildando tasks |
| `/opsx:archive <nombre>` | Solo después de revisión humana del usuario | Sincroniza specs, mueve a `archive/` |

**Reglas de oro:**
1. **Nunca archivar un change sin que el usuario lo revise primero.** Mostrar resultado y esperar OK.
2. **Nunca saltar fases** — si no hay proposal, no hay apply.
3. **Estado real lo dicta el CLI**, no asumir: `openspec list --json`, `openspec status --change <nombre> --json`.

---

## Skills — qué usar y en qué orden

Claude debe invocar la skill correspondiente **antes** de producir output. Orden por fase del trabajo:

### 1. Antes de proponer (fase de pensamiento)
| Skill | Cuándo |
|---|---|
| `pdf-reading` | La cátedra subió rúbrica/consigna en PDF y hay que extraer info. |
| `opsx:explore` (vía `/opsx:explore`) | Hay duda de enfoque o tradeoffs antes de comprometer un change. |

### 2. Al proponer y diseñar
| Skill | Cuándo |
|---|---|
| `opsx:propose` (vía `/opsx:propose`) | Crear change formal con proposal + design + tasks. |
| `web-artifacts-builder` | Prototipar un componente o pantalla **en el chat** antes de llevarlo al repo (mockup rápido). |

### 3. Al implementar
| Skill | Cuándo |
|---|---|
| `opsx:apply` (vía `/opsx:apply`) | Implementar las tasks del change. |
| `frontend-design` | Tocar React, Tailwind, dashboard con recharts, formularios con TanStack Form, o cualquier decisión visual/UX. |
| `mcp-builder` | Construir un MCP server custom (raro en este proyecto). |
| `skill-creator` | Crear una skill específica del proyecto (ej. una skill que cargue las RN-* automáticamente). |

### 4. Al revisar / cerrar
| Skill | Cuándo |
|---|---|
| `simplify` | Revisar código recién cambiado para reuso, calidad, eficiencia. |
| `judgment-day` | Review adversarial doble (dos jueces independientes) cuando hay dudas o el cambio es crítico. |
| `opsx:archive` (vía `/opsx:archive`) | Cerrar el change DESPUÉS de revisión humana. |

**Backend Python (FastAPI / SQLModel / Alembic)**: no hay skill dedicada. Regla: (1) consultar `context7` MCP para la doc actual, (2) respetar la regla de oro de imports (ver `AGENTS.md`), (3) envolver toda operación multi-tabla en el UoW.

**`engram:memory` está siempre activo** — guardar decisiones, bugfixes, convenciones proactivamente sin que el usuario lo pida.

---

## Modelos de preferencia por fase de delegación

Cuando el orquestador delega a un sub-agente, usar este mapping:

| Fase | Modelo | Razón |
|------|--------|-------|
| Orchestrator (vos) | `opus` | Coordina, decide, sintetiza |
| `opsx-explore` | `sonnet` | Lee código, thinking partner |
| `opsx-propose` | `opus` | Decisiones arquitectónicas, escribe artifacts |
| `opsx-apply` | `sonnet` | Implementación mecánica |
| `opsx-archive` | `haiku` | File ops, sincronización mecánica |
| Default (otra delegación) | `sonnet` | Lectura/escritura general |

Si no tenés acceso a un modelo (ej. sin Opus), bajar a `sonnet` y seguir.

---

## Convenciones del usuario (no negociables)

1. **NUNCA archivar un change sin revisión humana previa.** Mostrar el resultado, esperar OK explícito.
2. **pnpm**, no npm. En cualquier task, spec o doc que mencione package manager.
3. **Nunca commits con "Co-Authored-By"** ni atribución a IA. Conventional commits limpios.
4. **Nunca buildear después de cambios** salvo pedido explícito.
5. **Nunca usar `cat`/`grep`/`find`/`sed`/`ls`** — usar `bat`/`rg`/`fd`/`sd`/`eza`.
6. **Verificar antes de afirmar.** Ante reclamo del usuario: "dejame verificar" + chequear código/docs.

---

## MCPs (Claude Code)

Archivo de config: `.mcp.json` en la raíz. Servidores y reglas de uso → `AGENTS.md`.
Resumen rápido: `github` (PRs/issues), `postgres` (read-only a BD dev), `context7` (docs actualizadas de FastAPI/SQLModel/TanStack/etc.).
