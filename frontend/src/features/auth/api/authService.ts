import axios from 'axios'
import { apiClient } from '../../../shared/api/client'
import type { RolCode } from '../../../entities/user/model'
import type {
  AuthSuccessResponse,
  LoginRequest,
  RegisterRequest,
  TokenPair,
} from './types'

interface BackendTokenPairResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

interface BackendUserResponse {
  id: number
  nombre: string
  apellido: string
  email: string
  roles: string[]
}

async function fetchMe(accessToken: string): Promise<AuthSuccessResponse['user']> {
  const { data } = await apiClient.get<BackendUserResponse>('/api/v1/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return {
    id: data.id,
    nombre: data.nombre,
    email: data.email,
    roles: data.roles.map((codigo) => ({ id: 0, codigo: codigo as RolCode })),
  }
}

function mapTokens(raw: BackendTokenPairResponse): TokenPair & { tokenType: string; expiresIn: number } {
  return {
    accessToken: raw.access_token,
    refreshToken: raw.refresh_token,
    tokenType: raw.token_type,
    expiresIn: raw.expires_in,
  }
}

export async function register(data: RegisterRequest): Promise<AuthSuccessResponse> {
  const { data: raw } = await apiClient.post<BackendTokenPairResponse>('/api/v1/auth/register', data)
  const tokens = mapTokens(raw)
  const user = await fetchMe(tokens.accessToken)
  return { ...tokens, user }
}

export async function login(data: LoginRequest): Promise<AuthSuccessResponse> {
  const { data: raw } = await apiClient.post<BackendTokenPairResponse>('/api/v1/auth/login', data)
  const tokens = mapTokens(raw)
  const user = await fetchMe(tokens.accessToken)
  return { ...tokens, user }
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  const { data } = await axios.post<BackendTokenPairResponse>(
    `${import.meta.env.VITE_API_URL ?? ''}/api/v1/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' } }
  )
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  }
}

export async function logout(refreshToken: string): Promise<void> {
  try {
    await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken })
  } catch {
    // best-effort — local state is always cleared by the caller
  }
}
