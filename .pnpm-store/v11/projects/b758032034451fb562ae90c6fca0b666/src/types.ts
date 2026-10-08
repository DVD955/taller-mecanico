export type UserRole = 'ADMINISTRADOR' | 'RECEPCIONISTA' | 'MECANICO'
export type UserStatus = 'ACTIVO' | 'INACTIVO'

export interface User {
  id: number
  username: string
  full_name: string
  email: string | null
  role: UserRole
  status: UserStatus
  active_session: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: User
}

