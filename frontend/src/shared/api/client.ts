import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { env } from '../config/env'
import { authStore } from '../stores'

/**
 * Create a centralized Axios instance with base configuration
 * - Base URL from environment
 * - Default headers
 * - 30s timeout
 * - Request/response interceptors for JWT and error handling
 */

const createHttpClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: env.API_URL,
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  })

  // Request interceptor: Attach Authorization header if token exists
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = authStore.getState().token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor: Handle 401 and other errors
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // 401 Unauthorized - Clear auth state and redirect to login
        authStore.getState().logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
  )

  return client
}

export const apiClient = createHttpClient()

export default apiClient
