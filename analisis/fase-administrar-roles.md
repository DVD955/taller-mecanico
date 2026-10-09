# Tabla de fase: Administrar roles

Actor: administrador. Operaciones: consultar, cambiar nombre y datos, suspender con SoftDeleted, reactivar y asignar un rol activo a una cuenta. Se conserva la creación de cuentas de personal que ya existía.

| Fase | Definición |
|---|---|
| Precondiciones | Sesión válida de un administrador activo. El rol seleccionado existe, activo o suspendido. |
| Entradas | ID y versión del rol; nombre, descripción y estatus para actualizar; confirmación para la baja; cuenta y rol activo para asignar. |
| Validaciones | Solo administrador; campos y duplicados al cambiar nombre; versión vigente para evitar sobrescrituras; estatus 1 o 2 existente en el catálogo. Eliminar requiere confirmación y rol activo; repetir la suspensión no genera otra operación. Administrador e Invitado siguen protegidos para mantener el acceso y el registro. No se permite quitarse el rol administrador desde la sesión actual. |
| Ejecución | Abrir Administrar roles → consultar mediante INNER JOIN con status → seleccionar → actualizar nombre/datos/estatus o confirmar eliminación lógica → validar → bloquear fila → persistir → auditar → refrescar. Eliminar cambia Activo (1) a Suspendido (2). Para asignar: seleccionar cuenta y rol activo → validar → guardar asociación → auditar. |
| Postcondición | Actualización: datos modificados y versión incrementada; cambiar el nombre no modifica el código interno ni otorga otros permisos. SoftDeleted: `bin_status=2`, registro y asociaciones conservados, visible con estatus Suspendido. Sus cuentas no pueden acceder mientras el rol esté suspendido, incluso con una sesión abierta. Reactivar asigna 1 al mismo registro. Asignación: la cuenta referencia un rol activo. |
| Auditoría | Quién actuó, entidad e ID, acción `ACTUALIZAR_ROL`, `BAJA_LOGICA_ROL`, `ASIGNAR_ROL` o `CREAR_CUENTA_PERSONAL`, y hora UTC. |
| Respuesta | 200: operación completada; 201: cuenta de personal creada; 401/403: sin autorización; 404: registro inexistente; 409: duplicado, versión anterior, rol protegido o ya suspendido; 422: datos inválidos. |

## Catálogo de estatus

Tabla MySQL `status`, columnas `id`, `valor` y `descripcion`. En roles, `bin_status` es un **ID entero con llave foránea**, no un campo SQL BIT ni una repetición del texto del estatus.

| ID | Valor | Descripción |
|---|---|---|
| 1 | activo | Usuario o registro activo. |
| 2 | suspendido | Usuario o registro suspendido; se conserva. |

El ID 3 se conserva únicamente por compatibilidad con las bajas de clientes/talleres ya desarrolladas. La baja de roles **no usa 3**. La migración convierte antiguos roles con 3 a 2 sin borrar registros; el catálogo cambia el antiguo valor 2 `inactivo` por `suspendido`. Usuarios y clientes también almacenan únicamente `bin_status` con llave foránea a `status.id`; sus antiguas columnas de texto `status` se retiraron con respaldo, conservando los estados y los contratos HTTP.

Consulta equivalente a la utilizada por el backend:

```sql
SELECT r.id, r.name, r.bin_status, s.valor, s.descripcion
FROM roles AS r
INNER JOIN status AS s ON s.id = r.bin_status;
```

Diagrama: [Administrar roles](diagramas/02-administrar-roles/administrar-roles.html).
