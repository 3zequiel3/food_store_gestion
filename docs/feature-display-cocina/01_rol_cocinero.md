# 01 — Actor Cocinero y RBAC (delta)

> **Leer antes:** `knowledge-base/03_actores_y_roles.md`, `knowledge-base/05_reglas_de_negocio.md` (sección RN-RB y RN-FS).
> Este documento **agrega un actor** y **modifica** la tabla RBAC y la tabla de
> autorización del FSM. Las celdas modificadas están marcadas con 🆕.

---

## Nuevo actor: Cocinero (Rol: `COCINA`)

Se incorpora el **sexto actor** del sistema (quinto rol humano). Es un rol **operativo de
producción**: recibe los pedidos pagados y gestiona su preparación en tiempo real.

**Capacidades:**
- Visualizar, en una **pantalla de cocina en tiempo real** (KDS), los pedidos que ya
  fueron pagados y están listos para preparar (`CONFIRMADO`) y los que están en
  preparación (`EN_PREPARACIÓN`).
- Avanzar el FSM dentro de la **fase de cocina**:
  - `CONFIRMADO → EN_PREPARACIÓN` (toma el pedido / empieza a cocinarlo)
  - `EN_PREPARACIÓN → EN_CAMINO` (marca el pedido terminado y listo para despacho)
- Recibir por **push** (WebSocket) cada nuevo pedido confirmado, sin recargar la pantalla.
- *(Opcional — ver US-COCINA-07)* Marcar un producto como **no disponible**
  temporalmente cuando se agota un ingrediente (`Producto.disponible = false`).

**Restricciones:**
- **Sin CRUD.** No crea, edita ni elimina productos, categorías, ingredientes ni usuarios.
- **No despacha ni entrega.** `EN_CAMINO → ENTREGADO` es de `PEDIDOS` / `ADMIN`.
- **No cancela pedidos.** La cancelación sigue las reglas vigentes (RN-FS08): un pedido en
  `EN_PREPARACIÓN` solo lo cancela `ADMIN`.
- **No ve pedidos en `PENDIENTE`.** Un pedido sin pago aprobado **no es cocina todavía**.
  La cocina solo necesita saber qué cocinar; todo lo anterior (carrito, pago pendiente) es
  ruido que no le compete.

> **Coexistencia con `PEDIDOS`:** el Gestor de Pedidos **conserva** todas sus capacidades
> actuales sobre el FSM (incluidas las transiciones de cocina). El rol `COCINA` se agrega
> **en paralelo**, no reemplaza a `PEDIDOS`. En una tienda chica, una persona puede tener
> ambos roles. Esto evita romper lo ya definido en C-08 / C-10.

---

## Tabla RBAC actualizada

| Recurso / Acción | CLIENT | STOCK | PEDIDOS | **COCINA** 🆕 | ADMIN |
|------------------|:------:|:-----:|:-------:|:------------:|:-----:|
| Ver catálogo público | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gestionar carrito | ✅ | — | — | — | — |
| Crear pedido | ✅ | — | — | — | — |
| Cancelar pedido propio (PENDIENTE/CONFIRMADO) | ✅ | — | — | — | — |
| Ver mis pedidos | ✅ | — | — | — | — |
| Ver todos los pedidos | — | — | ✅ | — | ✅ |
| **Ver pantalla de cocina (KDS: CONFIRMADO + EN_PREPARACIÓN)** 🆕 | — | — | ✅ | **✅** | ✅ |
| Avanzar `CONFIRMADO → EN_PREPARACIÓN` | — | — | ✅ | **✅** 🆕 | ✅ |
| Avanzar `EN_PREPARACIÓN → EN_CAMINO` | — | — | ✅ | **✅** 🆕 | ✅ |
| Avanzar `EN_CAMINO → ENTREGADO` | — | — | ✅ | **—** | ✅ |
| Cancelar pedido EN_PREPARACIÓN | — | — | — | **—** | ✅ |
| **Marcar producto no disponible (`disponible`)** 🆕 *(opcional)* | — | ✅ | — | **✅** | ✅ |
| CRUD Productos / Categorías / Ingredientes | — | ✅ | — | — | ✅ |
| Modificar stock | — | ✅ | — | — | ✅ |
| Gestionar usuarios y roles | — | — | — | — | ✅ |
| Panel de métricas / dashboard | — | — | — | — | ✅ |

> La columna **COCINA** marca la diferencia respecto a `PEDIDOS`: la cocina **no ve el
> listado general de pedidos** ni puede despachar/entregar. Solo opera la pantalla de
> producción.

---

## Rol en la base de datos (delta de seed)

Se agrega un registro a la tabla catálogo `Rol` (PK semántica `codigo VARCHAR(20)`):

| Código | Nombre | Descripción |
|--------|--------|-------------|
| `COCINA` | Cocinero | Operación de cocina: recibe pedidos confirmados y gestiona su preparación |

- El seed (`INSERT ... ON CONFLICT DO NOTHING`) suma este registro a los 4 existentes.
- La relación sigue siendo N:M vía `UsuarioRol` (`rol_codigo` FK). Un usuario puede tener
  `COCINA` + `PEDIDOS` simultáneamente.
- Usuario de prueba sugerido para el seed de desarrollo: `cocina@foodstore.com`.

---

## Verificación de roles en el backend (delta)

Mismo patrón que el resto del sistema, con la dependencia `require_role`:

```python
# Endpoint del KDS: lo ven cocina, gestor de pedidos y admin
@router.get("/cocina/pedidos", dependencies=[Depends(require_role(["COCINA", "PEDIDOS", "ADMIN"]))])

# Avance de estado en fase de cocina
@router.patch("/pedidos/{id}/estado", dependencies=[Depends(require_role(["COCINA", "PEDIDOS", "ADMIN"]))])
```

> ⚠️ **Cuidado de seguridad:** que `COCINA` pueda llamar al endpoint de avance de estado
> **no** significa que pueda hacer *cualquier* transición. La validación de **qué
> transición permite cada rol** vive en el servicio del FSM (ver RN-CO-03 en
> `02_modelo_y_reglas.md`), no solo en el `require_role`. Un cocinero que intente
> `EN_CAMINO → ENTREGADO` debe recibir **403**, aunque pase el `require_role` del endpoint.

---

## Navegación por rol (frontend, delta)

- Al loguearse con rol `COCINA`, el menú/navegación debe llevar a la ruta `/cocina`
  (la pantalla KDS) como pantalla principal del rol.
- Guard de ruta: `/cocina` accesible si el usuario tiene `COCINA` **o** `PEDIDOS` **o**
  `ADMIN`.
- **La pantalla `/cocina` debe quedar siempre activa**: no aplicar auto-logout por
  inactividad sobre esta ruta (la pantalla de cocina vive encendida durante el turno).
