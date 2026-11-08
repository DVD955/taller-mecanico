// Reglas reales del modal; no abre navegador ni modifica datos.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { createRequire } = require('node:module')
const ts = require('../frontend/node_modules/typescript')
const modules = new Map()
function load(filename) {
  const absolute = path.resolve(__dirname, '../frontend/src/validation', filename)
  if (modules.has(absolute)) return modules.get(absolute)
  const compiled = ts.transpileModule(fs.readFileSync(absolute, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText
  const context = { exports: {}, require: name => name === './vehicleIdentifiers' ? load('vehicleIdentifiers.ts') : createRequire(absolute)(name) }
  vm.runInNewContext(compiled, context, { filename: absolute, timeout: 2000 })
  modules.set(absolute, context.exports)
  return context.exports
}
const { validateVehicleDraft, validateVehicleMileage, validateVehicleText } = load('vehicleForm.ts')
const valid = { vin: '1HGCM82633A004352', plate: 'ABC-123-D', make: 'Honda', model: 'Accord', year: '2003', version: 'EX', color: 'Gris', mileage: '0' }
let checks = 0
function check(result, expected, label) { assert.equal(result === true, expected, label); checks++ }
check(validateVehicleDraft(valid, true), true, 'Modificación completa')
const existing = { ...valid, vin: 'Q-ANTIGUO123' }
check(validateVehicleDraft(existing, true), true, 'Edición admite el VIN previo de solo lectura')
check(validateVehicleDraft(existing), false, 'Alta conserva la validación de VIN nuevo')
for (const field of Object.keys(valid)) {
  for (const value of ['', '   ', null]) check(validateVehicleDraft({ ...valid, [field]: value }, true), false, `${field} vacío/nulo`)
}
for (const value of ['0', '1', '10000000']) check(validateVehicleMileage(value, true), true, 'Kilometraje entero válido')
for (const value of ['-1', '1.5', '10000001', 'NaN', '1e3', undefined, true, false]) check(validateVehicleMileage(value, true), false, 'Kilometraje inválido')
check(validateVehicleDraft({ ...valid, mileage: '' }, false), true, 'Alta conserva kilometraje opcional')
check(validateVehicleDraft({ ...valid, mileage: null }, false), true, 'Alta conserva null opcional')
check(validateVehicleText(null, 'Marca', 60), false, 'Limpiar un campo no lanza excepción')
check(validateVehicleText('Honda\n', 'Marca', 60), false, 'Caracteres de control bloqueados')
check(validateVehicleText('x'.repeat(61), 'Marca', 60), false, 'Longitud máxima')
console.log(`RESULTADO: ${checks} comprobaciones del formulario de vehículos aprobadas.`)
