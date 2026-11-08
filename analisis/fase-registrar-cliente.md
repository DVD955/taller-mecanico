# TABLA FASE UC-CV-01 Registrar cliente

| Fase | Definición |
|---|---|
| Precondiciones | Administrador o recepcionista con cuenta, rol y sesión activos. Existe un taller activo. |
| Entradas | Taller seleccionado, nombre completo, calle, número, colonia, municipio, estado y al menos un contacto: correo, celular o alternativo. |
| Validaciones | Obligatoriedad, longitudes y formatos en frontend y backend. Normalización de nombre y contactos. Taller existente y activo. UC-CV-05 bloquea coincidencias de identidad o contacto, incluidos clientes dados de baja. |
| Ejecución | Abrir alta → seleccionar taller → capturar → normalizar → buscar coincidencias → revisar y confirmar → bloquear taller y verificar estado → persistir cliente/contactos → auditar → confirmar. |
| Postcondición | Customer activo, `bin_status=1`, relacionado a un taller por FK. La relación no puede modificarse desde la edición del cliente. |
| Auditoría | `audit_entries`: acción `UC-CV-01 RegistrarCliente`, actor de la sesión, cliente y hora UTC; misma transacción del cliente y sus contactos. |
| Respuesta | Revisión con coincidencias y sin token de confirmación si hay duplicados. Alta 201. 401/403 sesión o rol, 422 validación, 409 duplicado, 503 servicio no disponible. |

Builder construye el cliente validado; Strategy normaliza contactos; Bridge desacopla el caso de uso del adaptador MySQL. El token de revisión incluye taller, cliente normalizado y actor. La unicidad de contactos e identidad también se impone en MySQL, evitando altas dobles concurrentes.

Los clientes anteriores a esta migración conservan `workshop_id=NULL`; no se inventa su taller. Se muestran como «Sin taller · registro anterior». Toda alta nueva requiere taller.

Diagrama: [Registrar cliente](diagramas/04-clientes-vehiculos-20261009/01-registrar-cliente/registrar-cliente.html).
