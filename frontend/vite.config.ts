/// <reference types="vitest" />
import { defineConfig } from 'vite'
import { defineProject } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineProject(
  defineConfig({
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          // Default localhost para dev local; docker-compose lo pisa con
          // API_PROXY_TARGET=http://backend:8000 (service name de compose).
          target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      globals: true,
    },
  })
)
