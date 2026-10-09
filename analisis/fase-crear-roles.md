# Tabla de fase: Crear roles

Actor: administrador. Este proceso es distinto al registro público de una cuenta: **Crear cuenta → Registro → Invitado**. El formulario público no recibe ni permite seleccionar un rol.

| Fase | Definición |
|---|---|
| Precondiciones | Sesión válida; cuenta y rol activos; usuario con rol ADMINISTRADOR. |
| Entradas | Nombre obligatorio del rol (3–50 caracteres) y descripción opcional (máximo 200 caracteres). |
| Validaciones | Autorización en frontend y backend; nombre obligatorio; normalización de espacios y acentos; nombre y código únicos, también respecto de roles suspendidos por SoftDeleted. El registro público rechaza un campo `role` enviado manualmente. |
| Ejecución | Abrir el apartado independiente Crear rol → capturar → normalizar → buscar duplicados → guardar en una transacción → auditar → actualizar los roles de referencia. Para asignar, actualizar o dar de baja, pasar al apartado Administrar roles. Los índices únicos resuelven también intentos simultáneos. |
| Postcondición | Rol registrado con `bin_status=1`, referencia a `status.id`. Crear un rol no concede automáticamente los permisos de administrador o recepcionista. |
| Auditoría | `administration_audit`: ID de quien creó, entidad `roles`, ID del rol, acción `CREAR_ROL` y fecha/hora UTC. Se guarda junto al rol. |
| Respuesta | 201: rol creado; 401: sesión inválida; 403: no es administrador; 422: datos inválidos; 409: rol duplicado. |

La asignación de un rol a una cuenta se realiza después, únicamente desde la administración. El código interno del rol es estable; cambiar su nombre visible no cambia sus permisos.

Diagrama: [Crear roles](diagramas/01-crear-roles/crear-roles.html).
