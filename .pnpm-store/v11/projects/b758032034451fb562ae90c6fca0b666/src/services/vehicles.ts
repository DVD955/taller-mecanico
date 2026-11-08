import { ApiError, getToken } from '@/services/auth'
import type { SavedVehicle, Vehicle, VehicleInput } from '@/services/customers'
export { validateVehiclePhotos } from '@/validation/vehiclePhotos'

export interface VehiclePhoto { id: number; contentType: string; sizeBytes: number }
export interface VehicleAudit {
  id: number; actorUsername: string; customerId: number; previousCustomerId: number | null; action: string; occurredAt: string
}
export interface VehicleDetails {
  vehicle: Vehicle; customerName: string; workshopName: string | null; photos: VehiclePhoto[]; auditEntries: VehicleAudit[]
}
export interface VehicleListItem { vehicle: Vehicle; customerName: string; workshopName: string | null; photoCount: number }
export interface VehiclePage { items: VehicleListItem[]; total: number; page: number; pageSize: number }
async function response(path: string, method = 'GET', body?: BodyInit, json = false): Promise<Response> {
  let result: Response
  try {
    result = await fetch(`${import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8002'}/api/vehicles${path}`, {
      method, headers: { Authorization: `Bearer ${getToken() ?? ''}`, ...(json ? { 'Content-Type': 'application/json' } : {}) },
      ...(body === undefined ? {} : { body }),
    })
  } catch { throw new ApiError(0, 'No se pudo conectar con el servidor. Intenta nuevamente.') }
  if (!result.ok) {
    const error: { detail?: unknown } = await result.json().catch(() => ({}))
    throw new ApiError(result.status, typeof error.detail === 'string' ? error.detail : 'Revisa los datos del vehículo e intenta nuevamente.')
  }
  return result
}

function form(vehicle: VehicleInput, photos: File[], recordVersion?: number): FormData {
  const data = new FormData()
  data.append('payload', JSON.stringify({ vehicle, confirmed: true, ...(recordVersion === undefined ? {} : { recordVersion }) }))
  for (const photo of photos) data.append('photos', photo)
  return data
}

export const searchVehicles = async (page: number, search: string, status: string): Promise<VehiclePage> =>
  (await response(`?${new URLSearchParams({ page: String(page), page_size: '10', search, status })}`)).json() as Promise<VehiclePage>
export const getVehicleDetails = async (id: number): Promise<VehicleDetails> =>
  (await response(`/${id}`)).json() as Promise<VehicleDetails>
export const createVehicleWithPhotos = async (customerId: number, vehicle: VehicleInput, photos: File[]): Promise<SavedVehicle> =>
  (await response(`/customer/${customerId}`, 'POST', form(vehicle, photos))).json() as Promise<SavedVehicle>
export const updateVehicle = async (id: number, vehicle: VehicleInput, recordVersion: number, photos: File[]): Promise<SavedVehicle> =>
  (await response(`/${id}`, 'PUT', form(vehicle, photos, recordVersion))).json() as Promise<SavedVehicle>
export const deactivateVehicle = async (id: number, recordVersion: number): Promise<SavedVehicle> =>
  (await response(`/${id}`, 'DELETE', JSON.stringify({ recordVersion, confirmed: true }), true)).json() as Promise<SavedVehicle>
export const changeVehicleOwner = async (id: number, customerId: number, recordVersion: number): Promise<SavedVehicle> =>
  (await response(`/${id}/owner`, 'PUT', JSON.stringify({ customerId, recordVersion, confirmed: true }), true)).json() as Promise<SavedVehicle>
export const getVehiclePhotoUrl = async (id: number, photoId: number): Promise<string> =>
  URL.createObjectURL(await (await response(`/${id}/photos/${photoId}`)).blob())
