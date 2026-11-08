# Clientes, talleres y vehículos · 23 de octubre de 2026

Entrega basada en el texto del usuario, las dos imágenes de casos de uso y el audio `20261009_153330[1].m4a` (604 s). La [transcripción local automática](referencias/audio-20261009-transcripcion.txt) contiene frases imprecisas y se utiliza solo como apoyo; no es literal certificada.

El módulo de Administración de vehículos agrega expediente, búsqueda, edición, galería privada, baja lógica y cambio de cliente con historial. Admite hasta 10 fotos de 15 MB cada una. Desde el 5 de noviembre, el VIN queda fijo en la edición. Los siete campos editables son obligatorios, incluido el kilometraje (se acepta `0`), y se requiere al menos una foto existente o nueva. Kilometraje y fotos son opcionales en el alta. [Fases y verificación UC-CV-07..16](fase-administrar-vehiculos.md)

| Función | Administrador | Recepcionista | Secretaria | Mecánico/Invitado |
|---|---|---|---|---|
| Consultar clientes y sus vehículos | Sí | Sí | Sí | No |
| Registrar cliente asociado a un taller | Sí | Sí | No | No |
| Actualizar cliente en modal | Sí | No | Sí | No |
| Cambiar taller del cliente | No | No | No | No |
| Desactivar cliente sin borrar datos | Sí | No | No | No |
| Registrar vehículo para cliente activo | Sí | Sí | No | No |
| Consultar expediente y fotos de vehículo | Sí | Sí | Sí | No |
| Actualizar vehículo y agregar fotografías | Sí | Sí | No | No |
| Cambiar propietario/cliente del vehículo | Sí | Sí | No | No |
| Desactivar vehículo sin borrar datos/fotos | Sí | No | No | No |

Los permisos requieren cuenta y rol activos y una sesión vigente. La secretaria no obtiene administración de talleres ni roles. Su rol actual permanece suspendido.

El registro de vehículos no incorpora un «ID técnico independiente» como campo o identificador visible: solo VIN, placa y los datos del vehículo solicitados. No asigna técnicos ni mecánicos. Las claves internas de MySQL necesarias para conservar relaciones y auditoría no se capturan en pantalla.

Alcance de formatos confirmado el 14 de octubre: automóviles con **formatos de placa mexicanos**; no se agregan país ni provincia. El catálogo compartido reemplaza la aceptación genérica de cualquier combinación alfanumérica. El VIN conserva la estructura internacional y comprueba el dígito verificador cuando comienza por 1–5. Véanse los ejemplos, fuentes y límites en la tabla de fase del vehículo.

| Proceso | Resultado |
|---|---|
| UC-CV-01 Registrar cliente | Taller obligatorio y activo, FK, revisión y duplicados protegidos en transacción. |
| UC-CV-02 Consultar cliente | Listado, búsqueda, detalle con taller y vehículos. |
| UC-CV-03 Actualizar cliente | Modal precargado, permisos por operación, taller inmutable en frontend/FastAPI/C#. |
| UC-CV-04 Desactivar cliente | Estado del catálogo 2 y fecha de baja; conserva historial y vehículos. |
| UC-CV-05 Detectar duplicados | Identidad/contactos únicos, incluidos inactivos, comprobación antes y durante persistencia. |
| UC-CV-06 Registrar vehículo | Acción en tabla, cliente fijo, normalización, búsqueda previa de VIN/placa duplicados e índices únicos ante concurrencia, estado activo y auditoría. |

Tablas de fase: [registrar cliente](fase-registrar-cliente.md), [administrar clientes](fase-administrar-clientes.md), [duplicados](fase-detectar-duplicados.md) y [registrar vehículo](fase-registrar-vehiculo.md).

## Migración y conservación

El inicio de CustomerService ejecuta `database/customers.sql`, agrega `customers.workshop_id` si falta y su FK, y crea `vehicles` y `vehicle_audit_entries`. La ampliación agrega `vehicle_photos`, `record_version`, fechas de actualización/baja y cliente anterior de auditoría. Es repetible y conserva los registros existentes. No asigna arbitrariamente talleres a clientes antiguos ni modifica cuentas o sesiones existentes. Los registros anteriores sin taller siguen consultables/editables con su asociación vacía fija.

Se conserva un único estado persistido (`bin_status`) por entidad; el valor se obtiene del catálogo mediante `INNER JOIN`. Los nombres de talleres se consultan por relación, no se duplican en clientes.

## Verificación histórica · 14 de octubre

- TypeScript estricto/Vite: compilación correcta.
- C#: compilación correcta, cero errores y advertencias.
- Validadores TypeScript: 69 comprobaciones aprobadas, con el mismo catálogo y casos que el backend.
- Dominio C#: 101 comprobaciones aprobadas.
- Persistencia MySQL: 17 comprobaciones aprobadas, incluidas ocho operaciones concurrentes, rechazos por VIN/placa antes del alta sin auditorías adicionales y reversión ante fallos de auditoría.
- API/FastAPI/C#/MySQL: 68 comprobaciones aprobadas.
- Matriz de permisos del gateway: 25 combinaciones aprobadas.

Total de esa revisión: **280 comprobaciones funcionales aprobadas**. Las pruebas crean datos únicos y retiran únicamente esos datos al terminar. Se conservan la consulta explícita de duplicados antes de insertar, los campos del registro, sus permisos y la asociación fija al cliente durante el alta. Esta revisión fortaleció los formatos y sus mensajes en frontend/backend; no cambió datos existentes. Los resultados actuales están en la [verificación de la ampliación del 23 de octubre](fase-administrar-vehiculos.md#resultados-del-23-de-octubre-de-2026).

Los diagramas Archify son workflows de estas especificaciones de fase; no declaran evidencia de un commit Git que aún no contiene los cambios. Los diagramas de roles y alta de taller conservan su versión.

[Entrega de los tres diagramas, enlaces y recibos](diagramas/04-clientes-vehiculos-20261009/ENTREGA.md): los tres aprobados con validación showcase 9/9, cero errores/advertencias y `browser-check` automático. Revisión perceptual no realizada.

La revisión visual de la SPA mediante el navegador de la conversación fue rechazada por su política de URL. No se intentó eludir esa restricción. Las comprobaciones funcionales son de dominio, API y MySQL; no se atribuyen a pruebas visuales de esta versión.

Servicios locales reiniciados: FastAPI 8002 y CustomerService 8003. Vite permanece en 5176. Las nuevas cuentas Bene y Cris y las sesiones del usuario se conservan.
