import { ApiError, getToken } from './auth'
import { adminRequest } from './administration'

export interface PostalAddress { postal_code: string; state: string; municipality: string; neighborhood: string }
export interface Settlement extends PostalAddress { id: number }
export interface WorkshopDraft extends PostalAddress { name: string; rfc: string; email: string; street: string; number: string; version?: number }
export interface Workshop extends WorkshopDraft { id: number; version: number; status: string; bin_status: number; has_image: boolean }
const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8002'
export const getWorkshops = (): Promise<Workshop[]> => adminRequest('/api/workshops')
export const getStates = (): Promise<string[]> => adminRequest('/api/postal/states')
export const getMunicipalities = (state: string): Promise<string[]> => adminRequest('/api/postal/municipalities?' + new URLSearchParams({ state }))
export const getSettlements = (query: Record<string, string>): Promise<Settlement[]> => adminRequest('/api/postal/settlements?' + new URLSearchParams(query))
export const deleteWorkshop = (item: Workshop): Promise<{ message: string }> => adminRequest(`/api/workshops/${item.id}`, 'DELETE', { version: item.version })
export async function saveWorkshop(data: WorkshopDraft, image: File | null, id?: number): Promise<Workshop> {
  const body = new FormData()
  body.append('payload', JSON.stringify(data))
  if (image) body.append('image', image)
  const response = await fetch(`${API}/api/workshops${id ? '/' + id : ''}`, {
    method: id ? 'PUT' : 'POST', headers: { Authorization: `Bearer ${getToken() ?? ''}` }, body,
  })
  if (!response.ok) {
    const error: { detail?: string | Array<{ msg: string }> } = await response.json().catch(() => ({}))
    throw new ApiError(response.status, typeof error.detail === 'string' ? error.detail : error.detail?.map(row => row.msg).join('. ') ?? 'No se pudo guardar el taller.')
  }
  return response.json() as Promise<Workshop>
}
export async function getWorkshopImage(id: number): Promise<string> {
  const response = await fetch(`${API}/api/workshops/${id}/image`, { headers: { Authorization: `Bearer ${getToken() ?? ''}` } })
  if (!response.ok) throw new ApiError(response.status, 'No se pudo cargar la imagen del taller.')
  return URL.createObjectURL(await response.blob())
}
