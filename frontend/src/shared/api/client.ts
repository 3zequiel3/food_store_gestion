import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { env } from '../config/env'
import { useAuthStore } from '../stores'

/**
 * Create a centralized Axios instance with base configuration.
 * - Base URL from environment
 * - Default headers
 * - 30 s timeout
 * - Request/response interceptors for JWT and error handling
 *
 * NOTE: `useAuthStore.getState()` is the correct pattern to read store state
 * outside of React (e.g., inside Axios interceptors). See shared/stores/README.md.
 */

const createHttpClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: env.API_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  })

  // Request interceptor — attach Authorization header when an access token is available.
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = useAuthStore.getState().accessToken
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor — handle 401 by clearing auth and redirecting.
  // Full token-refresh logic will be added in the `auth-frontend-interceptor` change.
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )

  return client
}

export const apiClient = createHttpClient()

export default apiClient
