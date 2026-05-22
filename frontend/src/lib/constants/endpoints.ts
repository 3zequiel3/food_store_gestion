/**
 * Backend endpoint paths, relative to axios client baseURL (`/api/v1`).
 *
 * The feature code never writes `/api/v1/...` directly — it imports from here.
 * If the backend renames a route, this file is the only place to update.
 *
 * Sourced from:
 *   backend/main.py (router prefixes)
 *   backend/features/<feature>/router.py (paths inside each router)
 */

export const ENDPOINTS = {
  auth: {
    register: '/auth/register',
    login: '/auth/login',
    refresh: '/auth/refresh',
    logout: '/auth/logout',
    me: '/auth/me',
    token: '/auth/token',
  },

  usuarios: {
    me: '/usuarios/me',
    password: '/usuarios/me/password',
  },

  productos: {
    list: '/productos/',
    create: '/productos/',
    detail: (id: number) => `/productos/${id}`,
    update: (id: number) => `/productos/${id}`,
    delete: (id: number) => `/productos/${id}`,
    disponibilidad: (id: number) => `/productos/${id}/disponibilidad`,
    stock: (id: number) => `/productos/${id}/stock`,
    categorias: (id: number) => `/productos/${id}/categorias`,
    ingredientes: (id: number) => `/productos/${id}/ingredientes`,
    ingredienteDelete: (productoId: number, ingredienteId: number) =>
      `/productos/${productoId}/ingredientes/${ingredienteId}`,
  },

  pedidos: {
    list: '/pedidos',
    create: '/pedidos/',
    detail: (id: number) => `/pedidos/${id}`,
    estado: (id: number) => `/pedidos/${id}/estado`,
  },

  pagos: {
    // NOTE: create endpoint deprecated — use checkout.endpoints instead
    // create: '/pagos/',
    webhookMercadopago: '/pagos/webhook/mercadopago',
    porPedido: (pedidoId: number) => `/pagos/pedido/${pedidoId}`,
  },

  checkout: {
    online: '/checkout/online',
    pickupEfectivo: '/checkout/pickup-efectivo',
  },

  direcciones: {
    list: '/direcciones/',
    create: '/direcciones/',
    update: (id: number) => `/direcciones/${id}`,
    delete: (id: number) => `/direcciones/${id}`,
    predeterminada: (id: number) => `/direcciones/${id}/predeterminada`,
  },

  categorias: {
    list: '/categorias/',
    create: '/categorias/',
    update: (id: number) => `/categorias/${id}`,
    delete: (id: number) => `/categorias/${id}`,
  },

  ingredientes: {
    list: '/ingredientes/',
    create: '/ingredientes/',
    detail: (id: number) => `/ingredientes/${id}`,
    update: (id: number) => `/ingredientes/${id}`,
    delete: (id: number) => `/ingredientes/${id}`,
  },

  paymentMethods: {
    list: '/formas-pago',
  },

  adminUsuarios: {
    list: '/admin/usuarios',
    create: '/admin/usuarios',
    update: (id: number) => `/admin/usuarios/${id}`,
    cambiarRol: (id: number) => `/admin/usuarios/${id}/rol`,
    toggleEstado: (id: number) => `/admin/usuarios/${id}/estado`,
  },

  cocina: {
    pedidos: '/cocina/pedidos',
    transicionar: (id: number) => `/pedidos/${id}/transicionar`,
  },

  adminMetricas: {
    resumen: '/admin/metricas/resumen',
    ventasPorPeriodo: '/admin/metricas/ventas-por-periodo',
    topProductos: '/admin/metricas/top-productos',
    pedidosPorEstado: '/admin/metricas/pedidos-por-estado',
  },

  availability: {
    faltantes: '/availability/faltantes',
    resolver: (ingredienteId: number) => `/availability/faltantes/${ingredienteId}/resolver`,
  },
} as const;
