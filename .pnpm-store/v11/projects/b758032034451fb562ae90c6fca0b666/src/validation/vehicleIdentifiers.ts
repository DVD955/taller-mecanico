import specification from './vehicle-identifiers.json'

const controls = /[\u0000-\u001f\u007f-\u009f]/
const vinPattern = new RegExp(specification.vinPattern)
const platePatterns = specification.plateFormats.map(format =>
  new RegExp(`^${format.pattern.replaceAll('{L}', specification.plateLetters)}$`))
const letterValues: Readonly<Record<string, number>> = {
  A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8,
  J: 1, K: 2, L: 3, M: 4, N: 5, P: 7, R: 9,
  S: 2, T: 3, U: 4, V: 5, W: 6, X: 7, Y: 8, Z: 9,
}

export const normalizeVin = (value: string): string => value.trim().toUpperCase()
const plateText = (value: string): string => value.trim().toUpperCase().replace(/ +/g, ' ')
export const normalizeMexicanPlate = (value: string): string => plateText(value).replace(/[ -]/g, '')

export function validateVin(value: string): true | string {
  if (typeof value !== 'string' || controls.test(value) || !/^[a-zA-Z0-9]{17}$/.test(value.trim()))
    return specification.messages.vin
  const vin = normalizeVin(value)
  if (!vinPattern.test(vin)) return specification.messages.vin
  if ([...vin].every(character => character === vin[0])) return specification.messages.repeatedVin
  // El verificador norteamericano no se impone a los VIN extranjeros que
  // utilizan esa posición como parte de la descripción del fabricante.
  if (specification.checkDigitPrefixes.includes(vin[0] ?? '')) {
    const sum = [...vin].reduce((total, character, index) =>
      total + (letterValues[character] ?? Number(character)) * (specification.vinWeights[index] ?? 0), 0)
    const digit = sum % 11 === 10 ? 'X' : String(sum % 11)
    if (vin[8] !== digit) return specification.messages.checkDigit
  }
  return true
}

export function validateMexicanPlate(value: string): true | string {
  if (typeof value !== 'string' || controls.test(value) || !/^[a-zA-Z0-9 -]+$/.test(value.trim()))
    return specification.messages.plate
  const plate = plateText(value)
  if (plate.length > 20 || !platePatterns.some(pattern => pattern.test(plate))) return specification.messages.plate
  if (!/[1-9]/.test(plate)) return specification.messages.zeroPlate
  return true
}
