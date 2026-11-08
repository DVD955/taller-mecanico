import { validateMexicanPlate, validateVin } from './vehicleIdentifiers'

export interface VehicleDraft {
  vin: string | null
  plate: string | null
  make: string | null
  model: string | null
  year: string | null
  version: string | null
  color: string | null
  mileage: string | null
}

export function validateVehicleText(value: unknown, label: string, max: number): true | string {
  if (typeof value !== 'string' || !value.trim()) return `${label}: este campo es obligatorio.`
  if (/[\u0000-\u001f\u007f-\u009f]/.test(value)) return `${label}: no uses caracteres de control.`
  return value.length <= max || `${label}: máximo ${max} caracteres.`
}

export function validateVehicleYear(value: unknown, maximumYear = new Date().getFullYear() + 1): true | string {
  return typeof value === 'string' && /^\d{4}$/.test(value) && Number(value) >= 1900 && Number(value) <= maximumYear
    || `Año: utiliza un año entre 1900 y ${maximumYear}.`
}

export function validateVehicleMileage(value: unknown, required = false): true | string {
  if (value === null || value === undefined || value === '') return required ? 'Kilometraje: obligatorio para modificar el vehículo.' : true
  return typeof value === 'string' && /^\d+$/.test(value) && Number(value) <= 10000000
    || 'Kilometraje: utiliza un número entero entre 0 y 10000000.'
}

export function validateVehicleDraft(draft: VehicleDraft, editing = false): true | string {
  const vin = editing ? validateVehicleText(draft.vin, 'VIN', 17) : validateVin(draft.vin ?? '')
  const results = [vin, validateMexicanPlate(draft.plate ?? ''),
    validateVehicleText(draft.make, 'Marca', 60), validateVehicleText(draft.model, 'Modelo', 60),
    validateVehicleYear(draft.year), validateVehicleText(draft.version, 'Versión', 60),
    validateVehicleText(draft.color, 'Color', 40), validateVehicleMileage(draft.mileage, editing)]
  return results.find(result => result !== true) ?? true
}
