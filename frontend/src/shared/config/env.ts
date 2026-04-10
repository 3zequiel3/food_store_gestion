/**
 * Centralized environment configuration module
 * Reads and exports typed environment variables from .env files
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const IS_DEV = import.meta.env.DEV
const IS_PROD = import.meta.env.PROD

if (!API_URL) {
  console.warn('⚠️ VITE_API_URL not set in environment variables')
}

export const env = {
  API_URL,
  IS_DEV,
  IS_PROD,
} as const

export const { API_URL: VITE_API_URL } = env
export { IS_DEV, IS_PROD }
