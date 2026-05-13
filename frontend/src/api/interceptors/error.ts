import type { AxiosInstance, AxiosError } from 'axios';

/**
 * D6 — ApiError: clase que extiende Error para ser instanceof-checkable.
 *
 * El backend respeta RFC 7807 Problem Details. Los campos matchean el shape
 * que FastAPI retorna via HTTPException customizada en backend/core/exceptions.py.
 *
 * Uso en componentes:
 *   if (error instanceof ApiError && error.status === 409) { ... }
 *
 * Campos opcionales:
 *   - instance: URI específica del error (backfill si el backend lo incluye)
 *   - errors: array de errores field-level para validación de formularios
 */
export class ApiError extends Error {
  public readonly name = 'ApiError';

  constructor(
    public readonly type: string,
    public readonly title: string,
    public readonly status: number,
    public readonly detail: string,
    public readonly instance?: string,
    public readonly errors?: Array<{ field: string; message: string }>,
  ) {
    super(detail || title);
    // Necesario en ES5 targets para que instanceof funcione correctamente
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

/** Shape RFC 7807 que esperamos del backend */
interface Rfc7807Body {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: Array<{ field: string; message: string }>;
}

function buildNetworkError(): ApiError {
  return new ApiError(
    'about:blank',
    'Error de conexión',
    0,
    'No se pudo conectar al servidor',
  );
}

function parseApiError(axiosError: AxiosError): ApiError {
  if (!axiosError.response) {
    // Network error, timeout, CORS abort — sin response
    return buildNetworkError();
  }

  const { status, data } = axiosError.response;
  const body = data as Rfc7807Body;

  // Si el body es un objeto con al menos `title` o `detail`, asumimos RFC 7807
  if (body && typeof body === 'object' && (body.title || body.detail)) {
    return new ApiError(
      body.type ?? 'about:blank',
      body.title ?? `Error ${status}`,
      body.status ?? status,
      body.detail ?? '',
      body.instance,
      body.errors,
    );
  }

  // Fallback para responses no-RFC7807 (HTML de errores, CDN 5xx, etc.)
  return new ApiError(
    'about:blank',
    `Error ${status}`,
    status,
    typeof data === 'string' ? data : `Error del servidor (${status})`,
  );
}

/**
 * Registra el interceptor de error en la instancia axios recibida.
 * Se llama desde client.ts antes de exportar apiClient (D7).
 */
export function applyErrorInterceptor(client: AxiosInstance): void {
  client.interceptors.response.use(
    // Respuestas 2xx pasan sin modificar
    (response) => response,
    // Errores: siempre rechazar con ApiError para que los catch sean uniformes
    (error: AxiosError) => {
      return Promise.reject(parseApiError(error));
    },
  );
}
