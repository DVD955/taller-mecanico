# TABLA FASE · Administración de vehículos UC-CV-07..16

Requisitos tomados de `Grabación de pantalla 2026-10-22 175629.mp4`: consulta y administración (00:01–00:25), baja no física y duplicados (00:25–00:34), fotografías y asociación (00:34–01:05), máximo de **15 MB por fotografía** (01:12–01:26). La tabla visible incluye actualización, cambio de propietario, consultas relacionadas, resumen y auditoría. Se omiten los comentarios de clase ajenos al proyecto.

**Regla vigente desde el 5 de noviembre de 2026.** El modal muestra el VIN registrado en solo lectura. Para guardar se requieren placa mexicana, marca, modelo, año, versión, color y kilometraje completos, además de al menos una fotografía entre las existentes y las nuevas. El kilometraje `0` es válido. En el alta, kilometraje y fotografías continúan siendo opcionales.

| Fase | Definición |
|---|---|
| Precondiciones | Sesión, usuario y rol activos. Consultar: administrador, recepcionista o secretaria según los permisos existentes. Registrar/actualizar/asociar/cambiar cliente: administrador o recepcionista. Desactivar: solo administrador. Para una asociación nueva, el cliente destino debe estar activo. |
| Entradas | Búsqueda por VIN, placa, marca, modelo o cliente y filtros de estado y página. Edición con VIN registrado en solo lectura, siete campos editables obligatorios y al menos una foto entre anteriores y nuevas. Cliente destino para cambio de propietario. Revisión y confirmación para escrituras. |
| Validaciones | Rechazar campos omitidos, nulos, vacíos o con solo espacios y exigir kilometraje entero entre 0 y 10 000 000. Bloquear revisión y confirmación si faltan datos o fotografía. En edición, comparar el VIN recibido con el guardado dentro de la transacción. Aceptar el VIN de un registro anterior cuando coincida y aplicar la validación de formato de VIN en el alta. Conservar la validación y unicidad de placas. Admitir JPG/PNG/WebP reales sin animación de hasta 15 000 000 bytes cada una y comprobar el límite de 10 fotos acumuladas bajo bloqueo. |
| Ejecución | Abrir Administración de vehículos → buscar/filtrar → consultar expediente, cliente y galería → elegir acción → capturar → revisar y confirmar → validar permisos/datos → bloquear clientes y vehículo → comprobar duplicados/revisión → persistir cambios y fotos → registrar auditoría → confirmar transacción → actualizar listado. |
| Postcondición | La actualización conserva el VIN, el cliente y las fotos anteriores. Guarda los campos editables completos y agrega las fotos nuevas. El cambio de propietario conserva vehículo y fotos y registra el cliente anterior y el nuevo. La baja lógica guarda `bin_status=2`, `deleted_at` UTC y nueva revisión. El expediente inactivo continúa consultable. |
| Auditoría | `vehicle_audit_entries` conserva actor, usuario, vehículo, cliente, acción, fecha UTC y `previous_customer_id` cuando cambia el propietario. Se guardan datos, fotos y auditoría en la misma transacción; cualquier error revierte todo. La pantalla muestra los últimos 100 movimientos, sin borrar los anteriores. |
| Respuesta | 200 consulta/cambio/baja; 201 alta; 401 sesión; 403 permisos; 404 vehículo/foto/cliente no disponible; 409 duplicado, revisión antigua, vehículo inactivo o cliente destino inactivo; 413 foto/carga demasiado grande; 422 formatos, confirmación o cantidad; 503 servicio no disponible. |

## Cobertura de los casos mostrados

| Caso | Implementación |
|---|---|
| UC-CV-07 Consultar vehículo | Directorio paginado y búsqueda; expediente con identificación, estado, cliente, taller y galería privada. |
| UC-CV-08 Actualizar vehículo | Modal con VIN fijo, siete campos editables completos y una foto total obligatoria. Revisión, confirmación y control de concurrencia mediante `record_version`. |
| UC-CV-09 Desactivar vehículo | Solo administrador; `bin_status` referencia `status.id` mediante FK. Los textos de estado se obtienen con INNER JOIN; no se persiste texto redundante. |
| UC-CV-10 Detectar vehículo duplicado | Coincidencias por VIN o placa antes de insertar/actualizar y restricciones UNIQUE como protección concurrente. |
| UC-CV-11 Asociar vehículo a cliente | Alta desde clientes o selector de cliente activo en vehículos. |
| UC-CV-12 Cambiar propietario/cliente | Acción separada con confirmación, destino activo y auditoría de cliente anterior/nuevo. |
| UC-CV-13 Consultar vehículos de cliente | Detalle de cliente y acceso directo al expediente del vehículo. |
| UC-CV-14 Consultar cliente de vehículo | Datos asociados y modal de consulta del cliente; si fue dado de baja, se conserva su nombre y relación histórica. |
| UC-CV-15 Consultar resumen | Expediente con datos principales, relación, fotografías e historial. |
| UC-CV-16 Registrar auditoría | Automática y transaccional en alta, actualización, baja y cambio de cliente. |

## Persistencia y archivos

Migración aditiva e idempotente al iniciar CustomerService: revisión/fechas en `vehicles`, cliente anterior en auditoría y tabla `vehicle_photos`. Se conservan las filas existentes. `version` sigue siendo la versión comercial del automóvil; `record_version` es exclusivamente control interno de concurrencia.

Las fotografías se guardan como MEDIUMBLOB en MySQL, no en rutas públicas. La descarga exige sesión y permisos, verifica vehículo/foto y devuelve `Cache-Control: private, no-store` y `X-Content-Type-Options: nosniff`. FastAPI comprueba el contenido con Pillow y limita también cargas sin Content-Length. Las fotos siguen siendo opcionales en el alta según el video; la instrucción del 4 de noviembre exige una foto total al modificar. El límite de 10 es una medida operativa de tamaño/memoria, no un requisito atribuido al video.

API pública: `/api/vehicles`, `/api/vehicles/customer/{cliente}`, `/api/vehicles/{vehiculo}`, `/api/vehicles/{vehiculo}/owner` y `/api/vehicles/{vehiculo}/photos/{foto}`. La autorización se repite en el servicio C#; ocultar botones no es la protección de seguridad.

## Verificación

Ejecutar desde la raíz, con MySQL y ambas API disponibles para las integraciones:

```powershell
npm --prefix frontend run build
node tests/vehicle_identifiers.cjs
node tests/vehicle_form.cjs
node tests/vehicle_photos.cjs
backend\.venv\Scripts\python.exe tests/vehicle_photo_validation.py
backend\.venv\Scripts\python.exe tests/customer_permissions.py
backend\.venv\Scripts\python.exe tests/vehicle_management_integration.py
backend\.venv\Scripts\python.exe tests/customer_api_integration.py
```

Desde `customer-service/`: `dotnet run -- --self-test` y `dotnet run -- --integration-test`. Los fixtures usan UUID y se eliminan al terminar; no se cierran sesiones ni se cambian cuentas o estados de roles reales. La comprobación visual del navegador es independiente de las pruebas de API y compilación.

### Resultados del 23 de octubre de 2026

| Verificación ejecutada | Resultado |
|---|---|
| Compilación TypeScript/Vite y C# | Correctas; C# sin errores ni advertencias. |
| VIN/placas TypeScript | 69 comprobaciones aprobadas. |
| Fotografías TypeScript | 21 comprobaciones aprobadas. |
| Dominio y permisos C# | 148 comprobaciones aprobadas. |
| Validación real de fotografías Python | 5 pruebas unittest aprobadas, incluidos formatos, límite exacto y carga sin Content-Length. |
| Persistencia MySQL C# | 18 comprobaciones aprobadas; fallo de auditoría revierte también las fotos. |
| Integración HTTP/MySQL del video | 59 comprobaciones aprobadas. |
| Regresión HTTP/MySQL de clientes | 68 comprobaciones aprobadas. |
| Permisos del gateway | 25 combinaciones aprobadas. |

Los servicios quedan disponibles en 8002, 8003 y 5176. No se inicia sesión con cuentas reales para probarlos. No se realizó inspección visual automatizada de la SPA: la restricción previa de URL del navegador se conserva y no se intentó eludir. Los diagramas anteriores mantienen su carácter histórico; esta ampliación queda especificada en esta tabla de fases, sin atribuir a Archify un diagrama nuevo que no se haya generado.

### Verificación de modificación completa · 4 de noviembre de 2026

| Verificación ejecutada | Resultado |
|---|---|
| Compilación TypeScript/Vite y C# | Correctas; C# sin errores ni advertencias. |
| Formulario TypeScript | 41 comprobaciones aprobadas: ocho datos, vacíos/nulos/espacios y kilometraje cero. |
| Fotografías TypeScript | 27 comprobaciones aprobadas, incluidas galería obligatoria y fotos anteriores. |
| VIN/placas TypeScript | 69 comprobaciones aprobadas. |
| Dominio y permisos C# | 166 comprobaciones aprobadas. |
| Validaciones FastAPI/fotografías Python | 8 pruebas unittest aprobadas; los casos parametrizados cubren los ocho datos omitidos, vacíos o nulos. |
| Integración HTTP/MySQL de vehículos | 105 comprobaciones aprobadas: rechazo sin escrituras/auditorías ante datos incompletos o falta de foto; kilometraje cero, fotos anteriores, concurrencia, permisos y límites. |
| Regresión HTTP/MySQL de clientes | 68 comprobaciones aprobadas. |

Se conservaron las cuentas y sesiones reales; las pruebas de integración eliminaron sus registros temporales. Esta verificación comprueba compilación, validaciones y API; no incluye inspección visual automatizada. Los resultados del 23 de octubre permanecen como evidencia histórica.

### Verificación del VIN fijo · 5 de noviembre de 2026

Compilaron Vue y C#. Pasaron 41 comprobaciones del formulario, 166 del servicio C# y 109 de integración HTTP/MySQL. La integración verificó que la API guarda los siete campos editables, conserva el VIN y rechaza un VIN distinto aun cuando su formato sea válido. También comprobó el rechazo de campos nulos, omitidos o vacíos y la conservación del registro, sus fotos y su auditoría ante una solicitud inválida.

La verificación posterior de compatibilidad pasó 43 comprobaciones del formulario y 112 de integración. Un registro de prueba con VIN anterior admitió el cambio de color y conservó su VIN exacto. El mismo VIN fue rechazado al intentar usarlo en un alta nueva.
