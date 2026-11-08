// Validaciones de selección de fotos sin navegador ni archivos reales.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('../frontend/node_modules/typescript')
const source = fs.readFileSync(path.join(__dirname, '../frontend/src/validation/vehiclePhotos.ts'), 'utf8')
const context = { exports: {} }
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context)
const { validateVehiclePhotos: validate, MAX_VEHICLE_PHOTO_BYTES, MAX_VEHICLE_PHOTOS } = context.exports
let checks = 0
function check(value, expected) { assert.equal(value === true, expected); checks++ }
check(validate([]), true)
for (const type of ['image/jpeg', 'image/png', 'image/webp']) {
  check(validate([{ size: 1, type }]), true)
  check(validate([{ size: 15000000, type }]), true)
  check(validate([{ size: 15000001, type }]), false)
}
for (const type of ['image/gif', 'image/svg+xml', 'text/plain', '']) check(validate([{ size: 10, type }]), false)
check(validate([{ size: 0, type: 'image/png' }]), false)
check(validate(Array(10).fill({ size: 1, type: 'image/png' })), true)
check(validate(Array(11).fill({ size: 1, type: 'image/png' })), false)
check(validate(Array(2).fill({ size: 1, type: 'image/png' }), 8), true)
check(validate(Array(2).fill({ size: 1, type: 'image/png' }), 9), false)
check(validate([], 0, true), false)
check(validate([], 1, true), true)
check(validate([{ size: 1, type: 'image/png' }], 0, true), true)
check(validate([], 10, true), true)
check(validate([{ size: 1, type: 'image/png' }], 10, true), false)
check(validate([], 0, false), true)
assert.equal(MAX_VEHICLE_PHOTO_BYTES, 15000000)
assert.equal(MAX_VEHICLE_PHOTOS, 10)
console.log(`RESULTADO: ${checks + 2} comprobaciones de fotos en TypeScript aprobadas.`)
