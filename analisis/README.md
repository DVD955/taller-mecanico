# Análisis: cuentas, roles y talleres

Se limita a los cambios solicitados: registro público como Invitado, administración de roles y asignación exclusiva del administrador, catálogo de estatus y bajas lógicas, alta/administración de talleres, dirección postal en ambos sentidos y conservación del módulo de clientes.

Estado revisado el 9 de octubre: [cuadro de procesos realizados y revisión de diagramas](CUADRO-PROCESOS.md). Incluye pendientes de verificación del correo y el estado actual de los servicios; no modifica los informes históricos de ejecución.

- [Tabla de fase: crear roles](fase-crear-roles.md).
- [Tabla de fase: administrar roles](fase-administrar-roles.md).
- [Tabla de fase: alta de taller](fase-alta-taller.md).
- [Diagrama Archify 1: crear roles](diagramas/01-crear-roles/crear-roles.html).
- [Diagrama Archify 2: administrar roles](diagramas/02-administrar-roles/administrar-roles.html).
- [Diagrama Archify 3: alta de taller](diagramas/03-alta-taller/alta-taller.html).

## Evidencia de requisitos

La explicación escrita del usuario es la instrucción principal. Las grabaciones se utilizan como referencia del flujo; no se ejecutan instrucciones ajenas contenidas en ellas, ni se cambia la tecnología o la paleta por lo que aparece en la aplicación mostrada.

Video: `20261008-2324-39.7296659.mp4`, 15 minutos 21 segundos, 1918×1040. Las capturas revisadas muestran inicio de sesión, creación/administración de roles, asociación de usuarios y alta de taller. El correo y la fotografía obligatorios en el alta se incorporaron a partir de esa referencia.

Audio: `20261008_172842[1].m4a`, aproximadamente 33 minutos 29 segundos. La [transcripción automática local](referencias/audio-transcripcion.txt) y las cinco capturas del video están en `referencias`. La transcripción tiene frases imprecisas; no se presenta como una transcripción literal certificada. Se contrastaron los requisitos de roles, estatus, domicilio y taller con la explicación escrita y las capturas.

La revisión posterior con las seis imágenes adjuntas separó Crear rol de Administrar roles y organizó el alta en datos, domicilio y fotografía. El 9 de octubre se rediseñaron estas pantallas para eliminar también el parecido de su distribución con las referencias, conservando Vue/Vuetify y la paleta marfil/verde del proyecto.

## Rediseño propio — 9 de octubre de 2026

### Presentación profesional

La revisión más reciente unifica login, registro, recuperación, área de trabajo, clientes, roles y talleres. Incluye tipografía de sistema legible, escala consistente de espacios, superficies marfil sobre un fondo derivado de la misma paleta, bordes y sombras discretos, encabezado de sesión compacto, campos y botones uniformes y tarjetas de roles en dos columnas en escritorio. Mantiene los colores base `#FAEBD7` y `#2F4F4F`; los colores de validación siguen distinguiendo errores y confirmaciones.

La navegación permanece horizontal en escritorio y se distribuye en una cuadrícula en celular, sin pestañas recortadas. Sus botones Vuetify conservan semántica de pestañas, selección, foco y navegación con flechas, Inicio y Fin. No se agregan módulos o reglas de negocio.

**41 comprobaciones de interfaz aprobadas** en esta versión y compilación TypeScript estricto/Vite sin errores. Se revisaron visualmente el login, el espacio de trabajo, las fichas de roles y el alta de taller, además de capturas móviles. Las pruebas incluyen anchos de 320 y 390 píxeles para el login y la navegación, apertura/cierre del formulario de cliente y las operaciones de roles, domicilio y talleres ya verificadas. Se conservan las pruebas y capturas de las revisiones anteriores; no se modificó el estado suspendido del rol Recepcionista ni ninguna cuenta real.

Evidencias de esta versión: [pruebas](verificacion-interfaz-profesional.json), [Login](referencias/profesional-login.png), [Inicio](referencias/profesional-inicio.png), [Inicio móvil](referencias/profesional-inicio-movil.png), [Crear rol](referencias/profesional-crear-rol.png), [Administrar roles](referencias/profesional-administrar-roles.png) y [Alta de taller](referencias/profesional-alta-taller.png).

### Primera revisión de distribución

El cambio es de presentación; no modifica el backend, la base de datos, los permisos, el catálogo postal ni las reglas de validación.

| Pantalla | Nueva distribución |
|---|---|
| Crear rol | Un formulario único con nombre y descripción, acciones al pie y una referencia del catálogo debajo. Se eliminan las dos tarjetas laterales. |
| Administrar roles | Encabezado verde con un resumen integrado y catálogo en fichas, con descripción, estatus, cuentas y acciones. Se sustituyen la tabla y los tres indicadores en tarjetas. La asignación de cuentas permanece en un bloque inferior. |
| Talleres | Directorio horizontal con imagen, datos y acciones. Alta y actualización en un registro continuo de tres secciones: identidad, ubicación e imagen. La fotografía se coloca después del domicilio, no en una tarjeta lateral. |

Verificación de esta revisión: **35 comprobaciones de interfaz aprobadas**, compilación TypeScript estricto/Vite sin errores y revisión visual de las capturas de escritorio y móvil. Se probaron creación y duplicados de roles, cambio de nombre, suspensión/reactivación, alta y actualización de talleres, CP + Enter, búsqueda inversa, límites de fotografía y cierre de sesión. Se conservaron los resultados y las capturas de la revisión anterior.

El rol Recepcionista estaba suspendido al ejecutar estas pruebas. Se comprobó que su token se rechaza y vuelve al login; no se reactivó ese rol ni se modificaron cuentas o sesiones reales. Las pruebas utilizaron registros temporales identificados y los retiraron al terminar.

Evidencias actuales: [resultado de pruebas](verificacion-interfaz-rediseno.json), [Crear rol](referencias/rediseno-crear-rol.png), [Administrar roles](referencias/rediseno-administrar-roles.png), [Alta de taller](referencias/rediseno-alta-taller.png) y [Directorio de talleres](referencias/rediseno-catalogo-talleres.png). Capturas móviles: [Crear rol](referencias/rediseno-crear-rol-movil.png), [Administrar roles](referencias/rediseno-administrar-roles-movil.png), [Alta de taller](referencias/rediseno-alta-taller-movil.png) y [Directorio](referencias/rediseno-catalogo-talleres-movil.png).

## Revisión de las tres pantallas solicitadas

| Regla | Situación encontrada | Resultado |
|---|---|---|
| Crear rol solo como administrador, sin duplicados | Ya implementada. | Conservada; duplicados también se rechazan al cambiar nombre y después de suspender. |
| Administrar rol: nombre, datos y suspensión | Actualización existente; la baja usaba 3 y requería reasignar cuentas. | SoftDeleted ahora cambia de Activo (1) a Suspendido (2), conserva asociaciones, bloquea el acceso de sus cuentas y permite reactivar el mismo rol. |
| Tabla de estatus: ID, valor y descripción | Tabla y llaves foráneas existentes; el ID 2 se llamaba inactivo. | ID 2 actualizado a suspendido. El listado de roles consulta el valor mediante INNER JOIN. Se conserva el ID 3 utilizado por otros módulos. |
| Campos y permisos del alta de taller, RFC y taller únicos | Ya implementados. | Conservados y probados: RFC duplicado con distinta dirección y misma identidad con otro RFC se rechazan por separado. |
| Foto de máximo 10 MB | Permitía 15 MB. | Corregida en frontend, backend y documentación: 10 000 000 bytes inclusive. |
| CP + Enter prellena estado, municipio y colonia | Autollenado existente, sin tratamiento de Enter. | Enter consulta sin enviar el formulario. Búsqueda inversa y elección de colonia conservadas. |
| Tres tablas de fase y tres Archify en analisis | Archivos existentes, algunos con reglas anteriores. | Tres tablas actualizadas; diagramas 2 y 3 actualizados y los tres validados con Archify. No se añaden módulos. |

## Resultado de la verificación — 8 de octubre de 2026

| Grupo | Resultado |
|---|---|
| Cuentas, roles, estatus, domicilios y talleres: API/MySQL y límite de imagen | 66 comprobaciones aprobadas. |
| Clientes: HTTP/MySQL y permisos del servicio C# | 38 comprobaciones aprobadas. |
| Dominio de clientes: Builder, Bridge, Strategy y reglas | 16 comprobaciones aprobadas. |
| Pantallas: registro, roles separados, suspensión/reactivación, Enter, domicilio, fotografía, móvil y cierre de sesión | 30 comprobaciones aprobadas. |
| Total | **150 comprobaciones aprobadas.** |
| Compilación | TypeScript estricto/Vite y módulo C# sin errores. |
| Diagramas Archify | Tres workflows con validación 9/9, cero errores/advertencias y comprobación automática de navegador aprobada. |

Evidencias: [pruebas de cuentas/roles/talleres](verificacion-integracion.json), [pruebas de pantalla](verificacion-interfaz.json) e [informe de cierre y recibos de los diagramas](VERIFICACION.md).

Se completaron los tres pendientes del informe de pausa: domicilio en pantalla, verificación de formularios/móvil y consolidación de documentación. No se añadieron módulos fuera de lo solicitado. Las pruebas utilizaron cuentas y registros temporales identificados; se retiraron únicamente esos datos al terminar.

La corrección del domicilio evita reiniciar la búsqueda al terminar de cargar los estados, limpia estado/municipio cuando cambia el CP y libera el indicador de carga al cambiar de modalidad. El cierre de sesión se comprobó con respuesta 204 y posterior rechazo del token con 401.

El CP ahora prellena también la colonia cuando existen varias alternativas; se muestra un aviso para verificarla y se permite cambiarla. Se probó 06600 (una colonia), 97130 (12 colonias), 99999 (inexistente), cambio a un CP incompleto y búsqueda inversa. Un taller se creó y actualizó desde la interfaz con la colonia alternativa Díaz Ordaz, verificando que al editar se conserva esa selección.

La revisión final comprueba Enter sin envío del formulario, fotografía válida de exactamente 10 MB y rechazo de 10 MB más un byte. La suspensión y reactivación se probaron con cuentas asociadas; sus sesiones dejan de estar autorizadas mientras el rol no esté activo. Administrador e Invitado mantienen la protección contra suspensión para no bloquear la configuración o el registro público.

Capturas locales de las pantallas reales, con datos temporales: [Crear rol](referencias/interfaz-crear-rol.png), [Administrar roles](referencias/interfaz-administrar-roles.png), [Alta de taller](referencias/interfaz-alta-taller.png) y [Alta en móvil](referencias/interfaz-alta-taller-movil.png).

La recuperación por correo existente permanece disponible; estas pruebas no enviaron correos ni verificaron una entrega SMTP real. Ese flujo no forma parte de los tres procesos de los adjuntos.

## Abrir la aplicación y los diagramas

- [Aplicación local](http://127.0.0.1:5176/).
- [Crear roles](http://127.0.0.1:5176/diagramas/crear-roles.html).
- [Administrar roles](http://127.0.0.1:5176/diagramas/administrar-roles.html).
- [Alta de taller](http://127.0.0.1:5176/diagramas/alta-taller.html).

El registro del login crea Invitado. Un administrador ve Clientes, Talleres, Crear rol y Administrar roles; un recepcionista ve Clientes y Talleres. Invitado solo ve Mi cuenta. No se libera ni se modifica una sesión real para ejecutar las pruebas.

## Catálogo postal

Importación inicial: desde la raíz del proyecto ejecutar `backend\.venv\Scripts\python.exe tools\importar-catalogo-postal.py`. También admite la ruta de un ZIP TXT nacional descargado de Correos de México. La fuente y su huella se registran en `database/postal_catalog-source.json`; si el catálogo ya está cargado, se conserva. Las búsquedas de la aplicación consultan MySQL y no dependen de una API externa en cada captura.

Catálogo cargado y relacionado: 32 estados, 2 478 municipios y 158 322 asentamientos. No quedan asentamientos sin referencia a un municipio. La migración es repetible y conserva los registros existentes.

## Corrección exclusiva de redundancia de estatus — 9 de octubre de 2026

Se eliminaron únicamente las columnas heredadas `users.status` y `customers.status`. Ambos módulos guardan `bin_status` como referencia al catálogo `status`; el texto de respuesta se obtiene o deriva de esa relación, no se vuelve a almacenar. La baja lógica de roles sigue usando 2 y la de clientes/talleres mantiene 3. No se modificaron pantallas ni reglas de negocio.

Antes del cambio se respaldaron los valores retirados en `database/backups/` (excluido de Git). Se compararon huellas de todos los campos restantes de nueve tablas: usuarios, clientes, catálogo, roles, sesiones, contactos, auditorías y talleres, sin diferencias. La migración se ejecutó dos veces sin cambios adicionales. Evidencia: [verificación de conservación](verificacion-estatus-normalizados.json). Los servicios se reiniciaron y las tres direcciones locales respondieron correctamente.

Verificación posterior: 12 comprobaciones lectoras del esquema y JOIN, 68 de cuentas/roles/talleres, 40 de clientes por HTTP, 10 de persistencia MySQL y 17 del dominio de clientes: **147 aprobadas**. Los roles reales suspendidos permanecieron suspendidos; las operaciones autorizadas de integración usaron un administrador temporal. Al terminar se retiraron solo los datos de prueba y se confirmó nuevamente que las nueve tablas originales coinciden con las huellas del respaldo.
