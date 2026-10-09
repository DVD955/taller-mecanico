export type UserRole = string
export type UserStatus = 'ACTIVO' | 'INACTIVO' | 'ELIMINADO'

export interface User {
  id: number
  username: string
  full_name: string
  email: string | null
  role: UserRole
  role_name: string
  status: UserStatus
  bin_status: number
  active_session: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: User
}

