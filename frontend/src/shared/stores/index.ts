// ---------------------------------------------------------------------------
// Auth store
// ---------------------------------------------------------------------------
export {
  useAuthStore,
  selectIsAuthenticated,
  selectAccessToken,
  selectRefreshToken,
  selectUsuario,
  selectHasRol,
} from './authStore'

// ---------------------------------------------------------------------------
// Cart store
// ---------------------------------------------------------------------------
export {
  useCartStore,
  selectItems,
  selectTotalItems,
  selectTotalPrice,
  selectGetItem,
} from './cartStore'

// ---------------------------------------------------------------------------
// Payment store
// ---------------------------------------------------------------------------
export {
  usePaymentStore,
  selectCheckoutStep,
  selectPaymentStatus,
  selectPreferenceId,
  selectPaymentError,
} from './paymentStore'

// ---------------------------------------------------------------------------
// UI store
// ---------------------------------------------------------------------------
export {
  useUIStore,
  selectTheme,
  selectSidebarOpen,
  selectToasts,
} from './uiStore'

// ---------------------------------------------------------------------------
// Domain types — re-exported for consumer convenience
// (consumers can import directly from entities/* if they prefer)
// ---------------------------------------------------------------------------
export type { RolCode, Rol, Usuario, AuthTokens } from '../../entities/user/model'
export type { CartItem, Personalizacion } from '../../entities/order/model'
export type { Theme, Toast } from '../types/ui'
