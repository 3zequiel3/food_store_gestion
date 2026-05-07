import type { Usuario } from '../../../entities/user/model'

export interface RegisterRequest {
  nombre: string
  apellido: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenPair {
  accessToken: string
  refreshToken: string
}

export interface AuthSuccessResponse extends TokenPair {
  tokenType: string
  expiresIn: number
  user: Usuario
}
