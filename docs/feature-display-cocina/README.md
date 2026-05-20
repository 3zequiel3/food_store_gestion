# Feature Pack — Display de Cocina (KDS) + Rol Cocinero

> **Para el alumno:** este paquete es material de dominio que **falta** en la base de
> conocimiento original de Food Store. Lo agregás a tu proyecto y lo usás como insumo
> para proponer un nuevo *change* con SDD (`/opsx:propose`). **No es código** — es el
> QUÉ y el POR QUÉ. El CÓMO lo diseñás vos en el `proposal.md` / `design.md` del change.

---

## 1. Por qué existe este paquete

Food Store, tal como viene documentado, **no tiene display de cocina ni rol cocinero**.
La palabra "cocina" aparece solo como prosa descriptiva (ej. *"EN_PREPARACIÓN indica
que el equipo de cocina está trabajando"* en `docs/Descripcion.txt`), pero:

- El RBAC tiene **4 roles**: `ADMIN`, `STOCK`, `PEDIDOS`, `CLIENT`. **No hay COCINA.**
- Toda la operación de cocina está absorbida por el **Gestor de Pedidos** vía el FSM.
- No existe una pantalla dedicada que muestre los pedidos a preparar en tiempo real.

Esta feature porta el concepto de **Kitchen Display System (KDS)** desde un proyecto
hermano de servicio en mesa, **adaptándolo al modelo de delivery / e-commerce de Food
Store**. Se descartaron deliberadamente los conceptos que NO aplican (mesas, rondas,
mozo, sesiones, multi-sucursal): Food Store es una tienda de delivery, no un restaurante
con mesas.

---

## 2. Decisiones de diseño ya tomadas

Estas decisiones están **cerradas** y son la base del feature pack. Respetalas salvo que
tengas una razón técnica fuerte para cambiarlas (y si la tenés, documentala en
`/opsx:explore` antes).

| # | Decisión | Detalle |
|---|----------|---------|
| D-1 | **Tiempo real (alta fidelidad)** | El KDS recibe pedidos por **push** (WebSocket), no por recarga manual. Esto **agrega infraestructura nueva** al backend (ver §4). |
| D-2 | **El Cocinero es dueño de la fase EN_PREPARACIÓN** | **Sin estados nuevos** en el FSM. El cocinero ejecuta `CONFIRMADO → EN_PREPARACIÓN` (toma el pedido) y `EN_PREPARACIÓN → EN_CAMINO` (lo marca terminado / listo para despacho). |
| D-3 | **El despacho y la entrega NO son de cocina** | `EN_CAMINO → ENTREGADO` lo siguen ejecutando `PEDIDOS` / `ADMIN`. La cocina se ocupa solo de la preparación. |
| D-4 | **El rol COCINA no tiene CRUD** | Es un rol operativo de solo lectura + avance de estado. No crea, edita ni borra entidades de negocio. |

### Tradeoff honesto que tenés que entender (D-1)

Food Store **hoy no tiene WebSockets ni Redis**. Su stack es REST puro (FastAPI +
PostgreSQL). Implementar un KDS en tiempo real **es parte del trabajo del change**, no un
detalle. Vas a tener que:

- Agregar un endpoint WebSocket en FastAPI (`/api/v1/cocina/ws`) con auth por JWT.
- Implementar un mecanismo de publicación de eventos cuando un pedido cambia de estado.
- En un deploy de **una sola instancia**, alcanza con un pub/sub **en proceso** (`asyncio`,
  un `set` de conexiones activas). **No necesitás Redis para la versión single-instance.**
- Si en el futuro corre en **múltiples instancias**, ahí sí vas a necesitar un bus externo
  (Redis Pub/Sub o similar) para que el evento llegue a la instancia que tiene la conexión
  del cocinero. Dejá esto documentado como límite conocido.

> **Alternativa más liviana (válida):** para un flujo de un solo sentido (servidor →
> pantalla), **Server-Sent Events (SSE)** es más simple que WebSocket y encaja perfecto.
> Si lo elegís, justificá el cambio en `design.md`. El feature pack asume WebSocket por la
> decisión D-1, pero SSE es una decisión defendible.

### Tradeoff honesto del FSM (D-2)

Como **no** introdujimos un estado intermedio `LISTO` / `READY`, la señal de "cocina
terminó" es la transición `EN_PREPARACIÓN → EN_CAMINO`. En un delivery donde quien
despacha es un repartidor distinto del cocinero, esto mezcla dos eventos ("comida lista" y
"salió a reparto") en uno. Es aceptable para la v1 y mantiene el modelo simple.

Si tu equipo quiere separar ambos momentos, está documentado como **pregunta abierta** en
`02_modelo_y_reglas.md` (sección "Pregunta abierta PA-CO-01"). Esa sería una variante más
ambiciosa del change.

---

## 3. Qué contiene este paquete

| Archivo | Contenido | Espeja a |
|---------|-----------|----------|
| `01_rol_cocinero.md` | Definición del actor Cocinero + tabla RBAC actualizada | `knowledge-base/03_actores_y_roles.md` |
| `02_modelo_y_reglas.md` | Delta del modelo de datos, reglas de negocio `RN-CO-*`, delta del FSM, arquitectura de tiempo real | `knowledge-base/04`, `05`, `07` |
| `03_historias_de_usuario.md` | Historias de usuario `US-COCINA-01..09` con criterios de aceptación | `knowledge-base/06_funcionalidades.md` y `docs/Historias_de_usuario.txt` |

---

## 4. Cómo implementarlo con SDD (paso a paso para el alumno)

1. **Leé este paquete entero.** Conceptos antes que código. Siempre.
2. **Leé los docs de la KB que se citan** en cada archivo (campo "Leer antes").
3. Arrancá con `/opsx:explore display-cocina` para pensar el diseño (¿WebSocket o SSE?
   ¿single o multi-instancia? ¿cómo modelo el timer de urgencia?).
4. Corré `/opsx:propose C-11-display-cocina` y usá este material como insumo del
   `proposal.md`, `design.md`, `specs/` y `tasks.md`.
5. Implementá con `/opsx:apply` siguiendo TDD (tests primero — y los de integración le
   pegan a una PostgreSQL real, sin mockear la DB; los WebSocket sí se pueden testear con
   el `TestClient` de FastAPI).
6. Cerrá con `/opsx:archive`.

### Dependencias del change

Esta feature depende de que ya existan:

- **C-02 auth** (necesitás el rol y el `require_role`).
- **C-08 pedidos** (necesitás el FSM y el `HistorialEstadoPedido`).
- **C-09 pagos** (la entrada a la cola de cocina se dispara con `PENDIENTE → CONFIRMADO`,
  que ocurre cuando el pago es aprobado).

Por eso, en el roadmap, este change se ubica **después de C-09** (en paralelo o antes de
C-10 admin). Sugerencia de nombre: `C-11-display-cocina`.

---

## 5. Lo que este paquete NO trae (y por qué)

| Concepto de Jrmuela descartado | Por qué no aplica a Food Store |
|-------------------------------|-------------------------------|
| Mesas, sesiones, rondas (`round`) | Food Store es delivery: la unidad es `Pedido`, no una ronda en una mesa. |
| Rol WAITER (mozo) | No hay servicio en mesa. |
| Multi-tenant / multi-sucursal (`branch`) | Food Store es de una sola tienda. |
| Estaciones de cocina (BAR, GRILL, etc.) | Sobre-ingeniería para una v1. Se menciona como evolución futura, no como requisito. |
| Outbox Pattern + Redis Streams + DLQ | Infra pesada para un proyecto single-instance. La versión v1 usa pub/sub en proceso. |
