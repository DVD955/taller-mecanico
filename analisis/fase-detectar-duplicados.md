# TABLA FASE UC-CV-05 Detectar cliente potencialmente duplicado

| Fase | Definición |
|---|---|
| Precondiciones | Alta o edición de cliente autorizada. |
| Entradas | Nombre, dirección y contactos normalizados; ID interno del cliente solo para excluirlo al editar. |
| Validaciones | Identidad (nombre y dirección sin diferencias de acentos/mayúsculas), correo y teléfonos normalizados. Un celular que coincida con el alternativo de otro cliente también es duplicado. Incluye clientes inactivos/dados de baja. |
| Ejecución | Normalizar → buscar coincidencias → mostrar coincidencias o emitir token de revisión → al confirmar repetir búsqueda → verificar índices únicos al persistir. |
| Postcondición | Una coincidencia bloquea alta/edición. Una solicitud concurrente no crea un segundo registro. |
| Auditoría | No hay auditoría de alta/edición para un intento rechazado. La operación válida audita dentro de su transacción. |
| Respuesta | 200 con coincidencias y `previewToken=null` en revisión; 409 si el conflicto aparece al guardar. |

El taller no participa en la identidad del cliente: cambiar de taller en una captura nueva no permite duplicar a la misma persona. Los flujos de alta y administración incluyen este proceso en sus diagramas.
