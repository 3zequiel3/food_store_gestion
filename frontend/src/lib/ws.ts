/**
 * WebSocket URL builder — shared utility for all WS consumers.
 *
 * Reads VITE_WS_URL from the Vite env:
 * - If set and non-empty → uses it as the origin base (e.g. "wss://api.example.com"),
 *   strips a trailing slash, and appends `/ws?token=<encoded-token>`.
 * - If unset or empty → falls back to the current window.location (protocol + host),
 *   mapping https: → wss: and http: → ws:. This preserves the existing dev behavior
 *   where the Vite proxy forwards /ws to the backend.
 *
 * @param token - JWT access token to pass as the `token` query param.
 */
export function buildWebSocketUrl(token: string): string {
  const configuredOrigin = import.meta.env.VITE_WS_URL;

  if (configuredOrigin) {
    const base = configuredOrigin.replace(/\/+$/, '');
    return `${base}/ws?token=${encodeURIComponent(token)}`;
  }

  // Fallback: derive origin from window.location (dev proxy path).
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws?token=${encodeURIComponent(token)}`;
}
