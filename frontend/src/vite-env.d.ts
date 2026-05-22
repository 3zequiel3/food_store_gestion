/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  /** WebSocket origin for production. Leave unset in dev — the Vite proxy handles /ws. Example: wss://your-backend.up.railway.app */
  readonly VITE_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
