// Prueba las mismas entradas que C# sin abrir un navegador ni modificar la BD.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { createRequire } = require('node:module')
const ts = require('../frontend/node_modules/typescript')
const cases = require('./vehicle-identifiers.cases.json')
const formats = require('../frontend/src/validation/vehicle-identifiers.json').plateFormats
const sourcePath = path.resolve(__dirname, '../frontend/src/validation/vehicleIdentifiers.ts')
const compiled = ts.transpileModule(fs.readFileSync(sourcePath, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
}).outputText
const context = { exports: {}, require: createRequire(sourcePath) }
vm.runInNewContext(compiled, context, { filename: sourcePath, timeout: 2000 })
const { validateVin, normalizeVin, validateMexicanPlate, normalizeMexicanPlate } = context.exports
let count = 0
for (const [entries, validate, normalize] of [
  [cases.vins, validateVin, normalizeVin],
  [[...formats.map(format => ({ raw: format.example, canonical: format.canonical })), ...cases.plates], validateMexicanPlate, normalizeMexicanPlate],
]) {
  for (const entry of entries) {
    assert.equal(validate(entry.raw) === true, entry.canonical !== null, `Validación incorrecta: ${JSON.stringify(entry.raw)}`)
    if (entry.canonical !== null) assert.equal(normalize(entry.raw), entry.canonical)
    count++
  }
}
console.log(`RESULTADO: ${count} comprobaciones de VIN y placas mexicanas en TypeScript aprobadas.`)
