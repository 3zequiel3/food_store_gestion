const ABSOLUTE_IMAGE_URL_PATTERN = /^(https?:|data:|blob:)/i;
const API_SUFFIX_PATTERN = /\/api\/v\d+\/?$/;

function cleanBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

function normalizePath(value: string): string {
  return value.trim().replace(/^\/+/, '');
}

function backendOriginFromApiBaseUrl(): string {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

  try {
    const apiUrl = new URL(configuredApiBaseUrl, window.location.origin);
    return apiUrl.href.replace(API_SUFFIX_PATTERN, '').replace(/\/+$/, '');
  } catch {
    return window.location.origin;
  }
}

function imageBaseUrl(): string {
  const configuredImageBaseUrl = import.meta.env.VITE_IMAGE_BASE_URL;
  if (configuredImageBaseUrl) {
    return cleanBaseUrl(configuredImageBaseUrl);
  }

  return backendOriginFromApiBaseUrl();
}

/**
 * Resolve product image URLs returned by the backend.
 *
 * Supports:
 * - absolute S3/proxy URLs: https://...
 * - backend relative URLs: /uploads/... or /api/v1/productos/imagenes/...
 * - bare storage keys when VITE_IMAGE_BASE_URL is configured.
 */
export function resolveImageUrl(value?: string | null): string | undefined {
  const imageUrl = value?.trim();
  if (!imageUrl) return undefined;

  if (ABSOLUTE_IMAGE_URL_PATTERN.test(imageUrl)) {
    return imageUrl;
  }

  if (imageUrl.startsWith('//')) {
    return `${window.location.protocol}${imageUrl}`;
  }

  return `${imageBaseUrl()}/${normalizePath(imageUrl)}`;
}
