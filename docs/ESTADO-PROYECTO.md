# Estado del proyecto Taller Mecánico

Fecha de revisión: 7 de octubre de 2026. Inventario basado en el código actual y en consultas de diagnóstico de solo lectura. No se cambiaron usuarios, clientes, sesiones ni configuración SMTP para elaborar este documento.

## Guardado

El código, las tablas SQL, las pruebas, la solución C# y los diagramas de Archify ya estaban guardados en Git en la versión local `0cb3787`. Este documento añade un resumen del avance. Las contraseñas y claves de los archivos `.env` permanecen locales y excluidas de Git. El guardado de archivos y versiones no equivale a un respaldo de los registros de MySQL ni a una publicación en GitHub.

## Tabla de funcionalidades

Disponible significa implementada en el código actual; no implica que todas sus variantes tengan pruebas automatizadas. Parcial identifica una limitación concreta. Pendiente significa no implementada; algunos elementos son mejoras o módulos futuros fuera del alcance actual de autenticación y clientes.

| # | Funcionalidad | Estado | Alcance o limitación |
|---|---|---|---|
| 1 | Inicio de sesión, roles y estado del usuario | Disponible | Usuario y contraseña; ADMINISTRADOR, RECEPCIONISTA y MECANICO. Se bloquea el acceso de cuentas inactivas. |
| 2 | Contraseñas protegidas | Disponible | Hash seguro con Argon2; no se almacenan como texto plano. |
| 3 | Validación en frontend y backend | Disponible | Campos obligatorios, formatos, longitudes, credenciales y mensajes de error. |
| 4 | Sesión única y cierre de sesión | Disponible | Bloquea un segundo acceso mientras hay sesión vigente; cerrar sesión invalida su token. |
| 5 | Crear cuentas desde el login y el panel administrador | Disponible | Registro de recepcionistas o mecánicos; el formulario no permite crear administradores. El registro es público, no exclusivo del administrador. |
| 6 | Guardar correo de recuperación del usuario | Disponible | El usuario autenticado puede actualizar su correo; el sistema verifica formato y duplicados. |
| 7 | Recuperación por correo Gmail | Parcial | Formulario, SMTP y restablecimiento con token temporal programados; hay configuración SMTP local. FRONTEND_URL apunta a 5174 y la app actual usa 5176. Falta alinear esa URL y comprobar la recepción y uso del enlace. No se envió correo en esta revisión. |
| 8 | Registrar cliente — UC-CV-01 | Disponible | Nombre completo, calle, número, colonia, municipio y estado; al menos correo, celular o teléfono alternativo. Revisión y confirmación; cliente ACTIVO. |
| 9 | Directorio y consulta de clientes | Disponible | Listado, detalle, búsqueda por nombre/contacto/municipio y paginación. |
| 10 | Actualizar cliente — UC-CV-02 | Disponible | Modificar datos, normalizar, revisar coincidencias y confirmar; conserva el ID. |
| 11 | Eliminar cliente — UC-CV-03 | Disponible | Confirmación y baja lógica: INACTIVO y fuera del listado; no se borran su registro ni auditorías. |
| 12 | Permisos sobre clientes | Disponible | Consultar, registrar, actualizar y eliminar exigen ADMINISTRADOR o RECEPCIONISTA en UI, FastAPI y C#. Cualquier otro rol queda fuera de la lista permitida. |
| 13 | Normalización y bloqueo de duplicados | Disponible | Limpieza de nombres/direcciones, correo en minúsculas y teléfonos normalizados. Coincidencias por contacto o nombre y dirección; restricciones UNIQUE. |
| 14 | Auditoría y protección de cambios concurrentes | Disponible | Operador, cliente, acción y hora UTC; versión del cliente y bloqueo de fila; cliente/contactos/auditoría en una transacción con rollback. |
| 15 | Diseño responsivo de login y clientes | Disponible | Vue/Vuetify con la paleta del proyecto; tabla en escritorio y tarjetas en móvil. Búsqueda, carga, errores, formularios y diálogos de confirmación. |
| 16 | Patrones y diagramas Archify | Disponible | Builder, Bridge y Strategy en C#. Tablas de fases y diagrama actualizado con registro, edición y baja; evidencia automática de validación y navegador. |
| 17 | Rol CLIENTE y portal propio de clientes | Pendiente | Los registros de clientes del taller no son cuentas de acceso. No existe un rol CLIENTE en el catálogo de autenticación. |
| 18 | Separar roles públicos y roles de personal | Parcial | Actualmente cualquiera puede registrarse como recepcionista o mecánico. Falta definir un rol público y reservar la asignación de roles de personal para el administrador. Es un punto de seguridad a resolver antes de publicar. |
| 19 | Restaurar bajas y consultar auditorías en pantalla | Pendiente | Los datos y auditorías se conservan en MySQL, pero no hay interfaz de restauración ni visor del historial. La auditoría no guarda valores anteriores y nuevos de cada campo. |
| 20 | Otros módulos del taller | Pendiente | No están implementados vehículos, citas, órdenes de servicio, inventario, cobros/facturación ni reportes. Son módulos futuros, no parte del alcance actual. |
| 21 | Respaldo automático de MySQL y despliegue de producción | Pendiente | No hay flujo de backup/restauración de la base ni despliegue público con HTTPS. La ejecución actual es local. |

Resumen del inventario: **21 grupos: 15 disponibles, 2 parciales y 4 pendientes/no implementados**. El conteo corresponde a los grupos de esta tabla, no a pantallas, endpoints ni pruebas individuales.

## Evidencias y ejecución local

- Se verificó respuesta HTTP 200 de FastAPI (`http://127.0.0.1:8002/api/health`), CustomerService (`http://127.0.0.1:8003/health`), la SPA (`http://127.0.0.1:5176/`) y el diagrama (`http://127.0.0.1:5176/diagramas/gestionar-clientes.html`).
- El OpenAPI del servidor confirma que el endpoint de registro es público. El catálogo de roles del código contiene únicamente ADMINISTRADOR, RECEPCIONISTA y MECANICO.
- Se revisó solo la presencia de variables SMTP, sin imprimir contraseñas ni intentar enviar mensajes.
- En el último desarrollo se aprobaron **62 comprobaciones de clientes**: 16 de dominio, 8 de MySQL y 38 HTTP/MySQL; C# y TypeScript/Vite compilaron correctamente. No se volvieron a ejecutar estas pruebas al guardar este inventario y no se presentan como pruebas completas del correo o de todo el sistema.

## Documentación de referencia

- [UC-CV-01 RegistrarCliente](UC-CV-01-RegistrarCliente.md).
- [UC-CV-02/03 Gestión de clientes, API y evidencias](UC-CV-02-03-GestionClientes.md).
- [Diagrama actualizado de Archify](http://127.0.0.1:5176/diagramas/gestionar-clientes.html).

Prioridades sugeridas para la siguiente etapa: separar los roles del registro público, corregir/probar el enlace de recuperación y preparar un respaldo recuperable de MySQL. Este documento registra pendientes; no implementa esas modificaciones.
