import { getToken, request } from './auth'
import type { User } from '@/types'

export interface Role { id: number; code: string; name: string; description: string; bin_status: number; status: string; version: number }
export interface Account { id: number; username: string; full_name: string; role: string; role_id: number; role_name: string; status: string }
export interface Status { id: number; value: string; description: string }
export interface StaffInput { username: string; full_name: string; email: string; password: string; role_id: number }
export function adminRequest<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  return request<T>(path, { method, headers: { Authorization: `Bearer ${getToken() ?? ''}` },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }) })
}
export const getRoles = (): Promise<Role[]> => adminRequest('/api/admin/roles')
export const getAccounts = (): Promise<Account[]> => adminRequest('/api/admin/users')
export const getStatuses = (): Promise<Status[]> => adminRequest('/api/admin/status')
export const createRole = (name: string, description: string): Promise<Role> => adminRequest('/api/admin/roles', 'POST', { name, description })
export const updateRole = (role: Role): Promise<Role> => adminRequest(`/api/admin/roles/${role.id}`, 'PUT', { name: role.name, description: role.description, bin_status: role.bin_status, version: role.version })
export const deleteRole = (role: Role): Promise<{ message: string }> => adminRequest(`/api/admin/roles/${role.id}`, 'DELETE', { version: role.version })
export const assignRole = (userId: number, roleId: number): Promise<{ message: string }> => adminRequest(`/api/admin/users/${userId}/role`, 'PUT', { role_id: roleId })
export const createStaff = (data: StaffInput): Promise<User> => adminRequest('/api/admin/users', 'POST', data)
