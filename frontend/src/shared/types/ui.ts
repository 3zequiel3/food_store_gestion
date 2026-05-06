/** Application theme preference. */
export type Theme = 'light' | 'dark'

/** In-app notification / toast message. */
export interface Toast {
  id: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  /** Auto-dismiss duration in ms. If omitted, the toast stays until dismissed. */
  durationMs?: number
}
