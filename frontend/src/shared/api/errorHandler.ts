import type { AxiosError } from 'axios'
import { useUIStore } from '../stores'

interface Rfc7807Body {
  detail?: string
  errors?: Array<{ field?: string; message?: string }>
}

export function handleApiError(error: AxiosError): void {
  const status = error.response?.status

  // 401 is handled by the refresh interceptor — no toast
  if (status === 401) return

  let message = 'Ocurrió un error inesperado'

  if (!error.response) {
    message = 'Error de conexión, revisá tu red'
  } else {
    const body = error.response.data as Rfc7807Body
    if (body?.errors?.[0]?.message) {
      message = body.errors[0].message
    } else if (body?.detail) {
      message = body.detail
    }
  }

  useUIStore.getState().pushToast({
    id: crypto.randomUUID(),
    message,
    level: 'error',
  })
}
