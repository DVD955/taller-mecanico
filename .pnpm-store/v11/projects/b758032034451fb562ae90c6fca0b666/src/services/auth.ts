import type { LoginResponse, User } from '@/types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'taller_access_token'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const body: { detail?: string | Array<{ msg: string }> } = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : body.detail?.map(item => item.msg).join('. ')
    throw new ApiError(response.status, detail ?? 'No fue posible completar la operación.')
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

export async function register(username: string, fullName: string, email: string, password: string): Promise<User> {
  return request<User>('/api/auth/register', {
    method: 'POST', body: JSON.stringify({ username, full_name: fullName, email, password }),
  })
}

export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  return request<{ message: string }>('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) })
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await request<void>('/api/auth/reset-password', {
    method: 'POST', body: JSON.stringify({ token, new_password: newPassword }),
  })
}

export async function updateEmail(email: string): Promise<User> {
  return request<User>('/api/auth/email', { method: 'PUT', headers: { Authorization: `Bearer ${getToken() ?? ''}` }, body: JSON.stringify({ email }) })
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
