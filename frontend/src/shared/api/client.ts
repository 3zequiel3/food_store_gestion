import axios from 'axios'
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { env } from '../config/env'
import { useAuthStore } from '../stores'
import { handleApiError } from './errorHandler'
import { refresh as authRefresh } from '../../features/auth/api/authService'

type QueueItem = {
  resolve: (token: string) => void
  reject: (err: unknown) => void
}

let isRefreshing = false
let pendingQueue: QueueItem[] = []

function flushQueue(token: string | null, error: unknown): void {
  pendingQueue.forEach((item) => {
    if (token !== null) {
      item.resolve(token)
    } else {
      item.reject(error)
    }
  })
  pendingQueue = []
}

const createHttpClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: env.API_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  })

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

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

      if (error.response?.status === 401 && !originalRequest._retry) {
        const currentRefreshToken = useAuthStore.getState().refreshToken

        if (!currentRefreshToken) {
          useAuthStore.getState().logout()
          window.location.href = '/login'
          return Promise.reject(error)
        }

        if (isRefreshing) {
          return new Promise<string>((resolve, reject) => {
            pendingQueue.push({ resolve, reject })
          }).then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return client(originalRequest)
          })
        }

        originalRequest._retry = true
        isRefreshing = true

        try {
          const newTokens = await authRefresh(currentRefreshToken)
          useAuthStore.getState().updateTokens(newTokens)
          flushQueue(newTokens.accessToken, null)
          originalRequest.headers.Authorization = `Bearer ${newTokens.accessToken}`
          return client(originalRequest)
        } catch (refreshError) {
          useAuthStore.getState().logout()
          flushQueue(null, refreshError)
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }

      handleApiError(error)
      return Promise.reject(error)
    }
  )

  return client
}

export const apiClient = createHttpClient()

export default apiClient
