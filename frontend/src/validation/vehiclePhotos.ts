export const MAX_VEHICLE_PHOTO_BYTES = 15000000
export const MAX_VEHICLE_PHOTOS = 10

export function validateVehiclePhotos(files: File[], existingCount = 0, required = false): true | string {
  if (required && files.length + existingCount < 1) return 'Agrega al menos una fotografía para modificar el vehículo.'
  if (files.length + existingCount > MAX_VEHICLE_PHOTOS) return 'Se permiten hasta 10 fotos por vehículo.'
  for (const file of files) {
    if (file.size > MAX_VEHICLE_PHOTO_BYTES) return 'Cada foto debe pesar como máximo 15 MB.'
    if (!file.size || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return 'Selecciona fotos JPG, PNG o WebP válidas.'
  }
  return true
}
