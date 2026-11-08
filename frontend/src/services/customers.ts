import { ApiError, getToken } from '@/services/auth'

export interface CustomerInput {
  workshopId: number | null
  fullName: string
  address: { street: string; number: string; neighborhood: string; municipality: string; state: string }
  contacts: { email: string | null; mobile: string | null; alternative: string | null }
}
export interface Customer extends CustomerInput { id: number; status: string; version: number; workshopName: string | null }
export interface CustomerPage { items: Customer[]; total: number; page: number; pageSize: number }
export interface PreviewResult { customer: Customer; matches: Customer[]; previewToken: string | null }
export interface SavedCustomer {
  customer: Customer
  auditEntry: { id: number; actorId: number; actorUsername: string; customerId: number; occurredAt: string }
}
export interface VehicleInput {
  vin: string; plate: string; make: string; model: string; year: number; version: string; color: string; mileage: number | null
}
export interface Vehicle extends VehicleInput { id: number; customerId: number; status: string; recordVersion: number }
export interface SavedVehicle { vehicle: Vehicle; auditEntry: { actorUsername: string; occurredAt: string } }

async function request<T>(path: string, method: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/customers${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken() ?? ''}` },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    })
  } catch { throw new ApiError(0, 'No se pudo conectar con el servidor. Intenta nuevamente.') }
  if (!response.ok) {
    const error: { detail?: unknown } = await response.json().catch(() => ({}))
    throw new ApiError(response.status, typeof error.detail === 'string' ? error.detail : 'Revisa los datos del cliente e intenta nuevamente.')
  }
  return response.json() as Promise<T>
}

export const previewCustomer = (input: CustomerInput): Promise<PreviewResult> => request('/preview', 'POST', input)
export const registerCustomer = (customer: CustomerInput, previewToken: string): Promise<SavedCustomer> =>
  request('', 'POST', { customer, previewToken, confirmed: true })
export const listCustomers = (page: number, search: string): Promise<CustomerPage> =>
  request(`?${new URLSearchParams({ page: String(page), page_size: '10', search })}`, 'GET')
export const getCustomer = (id: number): Promise<Customer> => request(`/${id}`, 'GET')
export const previewCustomerUpdate = (id: number, customer: CustomerInput, version: number): Promise<PreviewResult> =>
  request(`/${id}/preview`, 'POST', { customer, version })
export const updateCustomer = (id: number, customer: CustomerInput, version: number, previewToken: string): Promise<SavedCustomer> =>
  request(`/${id}`, 'PUT', { customer, version, previewToken, confirmed: true })
export const deleteCustomer = (id: number, version: number): Promise<SavedCustomer> =>
  request(`/${id}`, 'DELETE', { version, confirmed: true })
export const listVehicles = (customerId: number): Promise<Vehicle[]> => request(`/${customerId}/vehicles`, 'GET')
export const registerVehicle = (customerId: number, vehicle: VehicleInput): Promise<SavedVehicle> =>
  request(`/${customerId}/vehicles`, 'POST', { vehicle, confirmed: true })
