# Cuadro de procesos realizados

Fecha de revisión: 9 de octubre de 2026, zona America/Mexico_City.

Inventario basado en código, diagramas y evidencias locales. **Completado** significa implementado, con las verificaciones registradas que se indican abajo; no significa que los servidores estén encendidos actualmente ni que se hayan probado todas las variantes. Esta revisión no ejecutó escrituras de prueba, envió correos, cambió reglas ni reinició servicios.

| # | Proceso | Estado | Resultado desarrollado |
|---|---|---|---|
| 1 | Inicio de sesión | Completado | Usuario y contraseña; validación de credenciales, cuenta y rol activos; errores claros. |
| 2 | Protección de contraseñas y validación | Completado | Hash Argon2; obligatoriedad, formato y longitud validados en frontend y backend. |
| 3 | Sesión única y cierre de sesión | Completado | Impide otro acceso con sesión vigente; cerrar sesión invalida el acceso. |
| 4 | Creación de cuenta desde el login | Completado | Registro público únicamente como Invitado, sin selector de rol y con rechazo de duplicados. |
| 5 | Cuentas de personal y asignación de roles | Completado | Solo administrador crea cuentas de personal y asigna roles activos. |
| 6 | Crear rol en apartado independiente | Completado | Solo administrador; nombre y descripción; normalización y bloqueo de duplicados. |
| 7 | Administrar roles | Completado | Cambiar nombre/datos, suspender y reactivar el mismo registro. SoftDeleted: Activo 1 → Suspendido 2; no borra roles ni asociaciones. |
| 8 | Catálogo de estatus y eliminación de redundancia | Completado | Tabla `status(id, valor, descripcion)`; `bin_status` con llave foránea. Consultas mediante INNER JOIN; se retiraron `users.status` y `customers.status`. |
| 9 | Registrar cliente — UC-CV-01 | Completado | Nombre, dirección y al menos un contacto; normalizar, buscar coincidencias, revisar y confirmar. Solo administrador y recepcionista activos. |
| 10 | Consultar y administrar el directorio de clientes | Completado | Listado, detalle, búsqueda y paginación; presentación adaptable a escritorio y celular. |
| 11 | Actualizar cliente — UC-CV-02 | Completado | Conserva ID, valida duplicados contra otros clientes y exige revisión, confirmación y versión vigente. |
| 12 | Dar de baja cliente — UC-CV-03 | Completado | Baja lógica con `bin_status=3` y `deleted_at`; conserva datos, contactos e historial, y lo retira del listado habitual. La API mantiene la respuesta INACTIVO. |
| 13 | Patrones Builder, Bridge y Strategy | Completado | Construcción del cliente, persistencia desacoplada y validación/normalización de contactos en el módulo C#. |
| 14 | Alta y administración de taller | Completado | Registrar, consultar, actualizar y dar de baja lógicamente; solo administrador y recepcionista activos. Datos de identidad, contacto y domicilio. |
| 15 | Unicidad del taller, RFC y fotografía | Completado | RFC validado con expresión regular y fecha, RFC e identidad únicos; JPG/PNG/WebP de máximo 10 000 000 bytes. No verifica inscripción ante SAT. |
| 16 | Dirección por código postal y búsqueda inversa | Completado | CP + Enter prellena estado, municipio y colonia; selección estado → municipio → colonia devuelve CP. Permite elegir entre varias colonias. |
| 17 | Auditoría y control de concurrencia | Completado | Operador, entidad/cliente, acción y hora UTC; transacciones, rollback, restricciones únicas y control de versiones. |
| 18 | Diseño profesional y responsivo | Completado | Login, registro, recuperación, clientes, roles y talleres adaptados a la paleta #FAEBD7 / #2F4F4F; navegación accesible y móvil. |
| 19 | Análisis, diagramas, pruebas y respaldo dirigido | Completado | Tablas de fase y Archify guardados; pruebas de integración/interfaz registradas. Respaldo previo a retirar columnas redundantes y comparación de nueve tablas sin diferencias. |
| 20 | Recuperación de cuenta por correo | Parcial | Formulario, token temporal de 15 minutos, cambio de contraseña y configuración Gmail SMTP presentes. Falta alinear `FRONTEND_URL` (5174) con el puerto usado por la SPA (5176) y verificar recepción/uso de un correo real. No se validó la contraseña SMTP ni se envió correo en esta revisión. |

**Resumen: 20 grupos; 19 completados y 1 parcial.** La comprobación del correo está pendiente; no equivale a un módulo de recuperación ausente.

## Estado de ejecución actual

La comprobación de puertos y HTTP de esta revisión encontró MySQL escuchando en 3306, pero ningún servicio escuchando en 5176 (SPA), 8002 (FastAPI) ni 8003 (clientes). Los intentos HTTP fueron rechazados. El proyecto fue ejecutado y verificado anteriormente, pero **ahora es necesario iniciar sus tres servicios** para usar la página y las vistas de diagramas mediante esas direcciones. No se reiniciaron durante este inventario.

## Revisión de los diagramas Archify

| Diagrama | Decisión | Motivo |
|---|---|---|
| [Crear roles](diagramas/01-crear-roles/crear-roles.html) | Conservar sin cambios | Ya representa administrador activo, duplicados, `bin_status=1` y auditoría. |
| [Administrar roles](diagramas/02-administrar-roles/administrar-roles.html) | Conservar sin cambios | Ya representa actualización, asignación, suspensión a 2, reactivación y relación con `status` mediante INNER JOIN. |
| [Alta de taller](diagramas/03-alta-taller/alta-taller.html) | Conservar sin cambios | Ya incluye permisos, CP en ambos sentidos, taller/RFC únicos, fotografía de 10 MB y auditoría. |
| [Gestión de clientes UC-CV-01/02/03](../.archify/architecture-gestion-clientes-20261008-162837/gestionar-clientes.html) | Conservar sin cambios | El registro, edición y baja lógica siguen el mismo flujo. ACTIVO/INACTIVO describe la respuesta y comportamiento del cliente; no una columna de texto que deba seguir almacenada. |

Se contrastaron nodos, relaciones y notas con el código actual. Las cuatro copias principales en `frontend/public/diagramas/` coinciden por SHA-256 con sus HTML canónicos. La ruta histórica `registrar-cliente-fases.html` sirve la misma vista integrada de gestión de clientes; también se conserva. No se modificaron candidatos, HTML, recibos o capturas, ni se declara una nueva validación ejecutada por Archify.

La eliminación de estatus redundantes modifica el almacenamiento interno, no estos procesos. Por ello **no fue necesario actualizar ni regenerar los diagramas**.

## Evidencia de verificaciones registradas

| Grupo | Último resultado documentado |
|---|---|
| Normalización del esquema y relaciones | 12 comprobaciones lectoras aprobadas. |
| Cuentas, roles y talleres: API/MySQL | 68 comprobaciones aprobadas. |
| Clientes por HTTP/MySQL | 40 comprobaciones aprobadas. |
| Persistencia MySQL de clientes | 10 comprobaciones aprobadas. |
| Dominio y patrones de clientes | 17 comprobaciones aprobadas. |
| Total de la última corrección de estatus | **147 aprobadas.** |
| Interfaz profesional, revisión anterior a la corrección | **41 aprobadas**, con compilación TypeScript/Vite correcta. No se suman como si hubieran sido ejecutadas nuevamente. |

Fuentes: [conservación de datos y pruebas de estatus](verificacion-estatus-normalizados.json), [cuentas/roles/talleres](verificacion-integracion.json), [interfaz profesional](verificacion-interfaz-profesional.json), [análisis](README.md) y [recibos históricos Archify](VERIFICACION.md). No se volvieron a ejecutar suites de integración en este inventario. En la última ejecución, el rol real Recepcionista estaba suspendido: se comprobó su bloqueo y se usaron cuentas temporales para las operaciones autorizadas, sin reactivarlo.

Las órdenes de servicio, vehículos, inventario, facturación, despliegue de producción y otras ampliaciones no forman parte de estos grupos; no se añadieron para completar este cuadro.
