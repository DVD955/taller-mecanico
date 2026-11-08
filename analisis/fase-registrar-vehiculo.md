# TABLA FASE UC-CV-06 Registrar vehículo

| Fase | Definición |
|---|---|
| Precondiciones | Administrador o recepcionista activos con sesión vigente. Cliente activo seleccionado desde Administración de clientes. |
| Entradas | VIN/número de serie, placa, marca, modelo, año, versión, color y kilometraje opcional. Cliente precargado y fijo durante el alta. Fotografías opcionales JPG/PNG/WebP: hasta 10, máximo 15 000 000 bytes por foto. |
| Validaciones | Frontend y backend comparten catálogo: VIN de 17 caracteres sin I/O/Q y últimos cuatro numéricos; bloquea caracteres repetidos y verifica el dígito de control cuando empieza por 1–5. Placa con estructura mexicana de automóvil, sin I/O/Q/Ñ; separadores solo entre grupos; parte numérica no formada únicamente por ceros. Se normaliza a mayúsculas y sin separadores. Marca/modelo/versión/color obligatorios; año 1900–año actual+1; kilometraje entero 0–10 000 000 o vacío. VIN y placa únicos en la BD. |
| Ejecución | Desde clientes o Administración de vehículos → seleccionar cliente activo → capturar → normalizar → validar fotografías reales, tipo, tamaño y cantidad → revisar/confirmar → bloquear cliente y verificar actividad → buscar coincidencias por VIN o placa → guardar vehículo, fotografías privadas, relación y estado → auditar en la misma transacción → responder. Los índices únicos también bloquean duplicados concurrentes. |
| Postcondición | Vehicle activo con `bin_status=1` y FK obligatoria a un cliente. Se puede consultar desde el detalle del cliente. |
| Auditoría | `vehicle_audit_entries`: actor, usuario, cliente, vehículo, acción `UC-CV-06 RegistrarVehiculo` y hora UTC; transacción compartida con vehículo y relación. |
| Respuesta | 201 vehículo asociado. 401/403 sesión/rol; 404 cliente no disponible; 409 cliente inactivo o VIN/placa duplicados; 422 datos/confirmación; 503 servicio no disponible. |

**Fuera del alcance actual: ID técnico independiente.** Por indicación del usuario, no se incorpora como campo del formulario, dato de entrada ni identificador visible del vehículo. La identificación visible es VIN y placa. Tampoco se registra una asignación de técnico o mecánico en esta fase.

Las claves primarias internas de la base de datos se conservan únicamente para las relaciones cliente–vehículo y la auditoría; no son un dato adicional que el usuario deba capturar. No se elimina ni modifica ninguna relación o información existente.

Por la última indicación se admiten **formatos mexicanos de automóvil**, no una cadena alfanumérica genérica. El catálogo compartido `frontend/src/validation/vehicle-identifiers.json` incluye series particulares estatales/CDMX actuales y anteriores, fronterizas, de servicio público, ecológicas y de autos antiguos. Ejemplos: `ABC-123-D`, `A12-BCD`, `ABC-12-34`, `123-ABC`. No se agregan campos de país ni provincia.

El VIN acepta fabricantes de cualquier origen. No se exige el dígito norteamericano a VIN de otros mercados: por ejemplo, admite una novena posición `Z` en una estructura europea. Esto es una validación local de estructura, no una consulta del fabricante, del tipo real de vehículo o de su existencia. No compara año/marca/modelo contra un registro externo.

Validar una estructura mexicana no demuestra que una matrícula exista, esté vigente o proceda realmente de México; otro país podría emitir una combinación parecida. No se consulta REPUVE ni un padrón vehicular. Los datos anteriores se conservan sin reinterpretarlos ni borrarlos.

Fuentes del catálogo: [NOM-001-SCT-2-2016, tabla C](https://sidof.segob.gob.mx/notas/docFuente/5442476), [series anteriores](https://dof.gob.mx/nota_detalle_popup.php?codigo=2049964), [estructura internacional del VIN](https://www.nsai.ie/certification/automotive/transport-schemes/world-manufacturer-identifier/) y [cálculo del dígito verificador](https://dof.gob.mx/normasOficiales/3939/SSP/SSP.htm).

La baja del cliente conserva sus vehículos y bloquea asociaciones nuevas. La entrega del video del 22 de octubre agrega consulta, edición, baja lógica y cambio de propietario: [Administrar vehículos, UC-CV-07..16](fase-administrar-vehiculos.md). No se agregan órdenes de servicio ni asignación de técnicos.

Diagrama: [Registrar vehículo](diagramas/04-clientes-vehiculos-20261009/03-registrar-vehiculo/registrar-vehiculo.html).

Verificación del 14 de octubre de 2026: compilación TypeScript/Vite y C# correctas; C# con cero errores/advertencias. Aprobadas 69 comprobaciones de validadores TypeScript, 101 de dominio C#, 17 de MySQL, 68 de API y 25 de permisos: **280 comprobaciones**. Se verifica que `VehicleInput` conserve sus ocho campos, sin ID técnico independiente ni país/provincia. Los mismos casos de identificadores se prueban en TypeScript y C#. No fue necesaria una migración de BD; se reinició solo CustomerService para cargar las reglas nuevas.
