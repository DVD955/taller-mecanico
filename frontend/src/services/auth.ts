import type { LoginResponse, RegisterResponse, User, UserRole } from '@/types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'taller_access_token'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const body: { detail?: string } = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? 'No fue posible completar la operación.')
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const data = await request<LoginResponse>('/api/auth/login', {
    method: 'POST', body: JSON.stringify({ username, password }),
  })
  sessionStorage.setItem(TOKEN_KEY, data.access_token)
  return data
}

export async function register(username: string, fullName: string, password: string, role: Exclude<UserRole, 'ADMINISTRADOR'>): Promise<RegisterResponse> {
  return request<RegisterResponse>('/api/auth/register', {
    method: 'POST', body: JSON.stringify({ username, full_name: fullName, password, role }),
  })
}

export async function resetPassword(username: string, recoveryCode: string, newPassword: string): Promise<void> {
  await request<void>('/api/auth/reset-password', {
    method: 'POST', body: JSON.stringify({ username, recovery_code: recoveryCode, new_password: newPassword }),
  })
}

export function getToken(): string | null { return sessionStorage.getItem(TOKEN_KEY) }

export async function getCurrentUser(): Promise<User> {
  const token = getToken()
  if (!token) throw new ApiError(401, 'No hay una sesión local.')
  return request<User>('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
}

export async function logout(): Promise<void> {
  const token = getToken()
  try {
    if (token) await request<void>('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
  } finally {
    sessionStorage.removeItem(TOKEN_KEY)
  }
}
