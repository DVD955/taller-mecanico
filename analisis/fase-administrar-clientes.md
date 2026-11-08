# TABLAS FASE UC-CV-02, UC-CV-03 y UC-CV-04 · Administración de clientes

El texto del usuario indica **administrador y secretaria** para actualizar. El audio (aprox. 103–169 s) y la primera imagen dicen recepcionista/administrador. Se aplica la indicación escrita: secretaria solo consulta y actualiza clientes; recepcionista consulta, registra clientes y registra vehículos. El rol Secretaria existente está suspendido; esta entrega no lo reactiva.

## UC-CV-02 Consultar cliente

| Fase | Definición |
|---|---|
| Precondiciones | Sesión, cuenta y rol activos: administrador, recepcionista o secretaria. |
| Entradas | Búsqueda por nombre, contacto o municipio; paginación; selección del cliente. |
| Validaciones | Rol autorizado, límites de búsqueda/página y cliente no dado de baja. |
| Ejecución | Abrir módulo → buscar → listar → seleccionar detalle → consultar dirección, contactos, taller y vehículos. |
| Postcondición | Información consultada sin modificar datos. No se solicitan identificadores de técnicos. |
| Auditoría | La consulta no crea una auditoría de modificación. |
| Respuesta | 200 con página o detalle. 401/403, 404 cliente no disponible, 422 búsqueda inválida. |

## UC-CV-03 Actualizar cliente

| Fase | Definición |
|---|---|
| Precondiciones | Administrador o secretaria activos y con sesión vigente. Cliente disponible. |
| Entradas | Datos actuales precargados en una ventana modal: nombre, dirección y contactos. Taller visible como información fija. Versión vigente y confirmación. |
| Validaciones | Mismos formatos y contactos del alta; exclusión del propio cliente al detectar duplicados. Se rechaza un `workshopId` distinto, incluso por petición directa a la API. Token firmado y control de versión evitan alterar la revisión o sobrescribir cambios concurrentes. |
| Ejecución | Clic en nombre o Actualizar → validar permiso → cargar cliente → modal precargado → editar → normalizar → buscar coincidencias → revisar → confirmar → bloquear fila → verificar versión y taller → actualizar → auditar. |
| Postcondición | Datos actualizados y versión incrementada. Taller original conservado. |
| Auditoría | `UC-CV-03 ActualizarCliente`, actor, cliente y hora UTC en la misma transacción. Las acciones de auditoría históricas conservan sus etiquetas originales. |
| Respuesta | 200 actualizado; 403 rol no autorizado; 422 intento de cambiar taller o formato inválido; 409 duplicados/versión antigua. |

## UC-CV-04 Desactivar cliente

| Fase | Definición |
|---|---|
| Precondiciones | Solo administrador activo con sesión vigente. Cliente disponible y versión vigente. |
| Entradas | Cliente seleccionado y confirmación en modal. |
| Validaciones | Permiso en FastAPI y C#, confirmación, existencia y versión. |
| Ejecución | Solicitar desactivación → explicar conservación de datos → confirmar → bloquear fila → cambiar `bin_status` de 1 a 2 → registrar `deleted_at` UTC → incrementar versión → auditar. |
| Postcondición | Cliente inactivo y retirado del directorio operativo. Se conservan cliente, taller, contactos, vehículos y auditorías. No admite nuevos vehículos. |
| Auditoría | `UC-CV-04 DesactivarCliente`, actor, cliente y hora UTC, atómica con la baja. No se duplica la auditoría al repetirla. |
| Respuesta | 200 inactivo. 403 rol, 404 ya dado de baja, 409 versión desactualizada. |

`bin_status` referencia `status.id`; los estados se consultan con `INNER JOIN`. La columna textual de estatus no se vuelve a crear. Las bajas históricas con estatus 3 se conservan. No se utiliza `DELETE FROM customers` en ninguna operación funcional; las pruebas limpian únicamente sus propios datos temporales.

La tabla incluye una acción **Asociar vehículo** para administrador y recepcionista, únicamente con cliente activo. Abre el flujo UC-CV-06 con ese cliente fijo.

Diagrama: [Administrar clientes](diagramas/04-clientes-vehiculos-20261009/02-administrar-clientes/administrar-clientes.html).
