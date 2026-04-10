/**
 * API Response and Error type definitions
 */

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  timestamp?: string
}

export interface ApiError {
  message: string
  statusCode: number
  details?: Record<string, unknown>
  timestamp?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
