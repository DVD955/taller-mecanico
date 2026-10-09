# Tabla de fase: Alta de taller mecánico

Actores: administrador y recepcionista (secretaría). Invitado, mecánico y otros roles sin ese permiso no pueden registrar ni administrar talleres o clientes.

| Fase | Definición |
|---|---|
| Precondiciones | Sesión válida; cuenta y rol activos; administrador o recepcionista; catálogo postal nacional cargado en MySQL. |
| Entradas | Nombre del taller, RFC, correo de contacto, calle, número, CP, estado, municipio, colonia/asentamiento. Fotografía obligatoria en el alta, JPG, PNG o WebP de máximo 10 MB (10 000 000 bytes). Al actualizar, reemplazarla es opcional. |
| Validaciones | Obligatorios y longitudes; formato de correo; RFC de 12 o 13 caracteres mediante expresión regular y fecha válida; dirección coherente con SEPOMEX; contenido real, tipo y tamaño de imagen; RFC único y nombre/dirección normalizados únicos, incluso frente a bajas. Estas comprobaciones se repiten en el backend. |
| Ejecución | Abrir alta → capturar → resolver dirección → normalizar → validar RFC/imagen → verificar duplicados → guardar taller e imagen → auditar → mostrar el taller. Por CP: escribir 5 dígitos y presionar Enter para prellenar estado, municipio y colonia sin enviar el formulario. Si hay varias, avisar y permitir elegir la correcta. También se consulta automáticamente al terminar de escribir. Al editar o volver a presionar Enter se conserva la colonia elegida. Sin CP: elegir estado → municipio → colonia y obtener automáticamente el CP correspondiente. |
| Postcondición | Taller persistido activo (`bin_status=1`), con correo e imagen almacenada en MySQL. No se crea un segundo registro para el mismo RFC o la misma identidad de taller. |
| Auditoría | ID del actor, entidad `workshops`, ID del taller, acción `REGISTRAR_TALLER` y hora UTC; misma transacción que el alta. |
| Respuesta | 201: taller registrado; 401/403: sin autorización; 404: dirección no encontrada; 409: duplicado; 413: imagen mayor a 10 MB; 422: RFC, datos, dirección o archivo inválidos. |

RFC: `^[A-ZÑ&]{3,4}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[A-Z0-9]{3}$`. Se normaliza a mayúsculas y se verifica que la fecha exista. Esta validación de formato no consulta la inscripción del contribuyente en el SAT.

La administración del taller permite consultar, actualizar con control de versión y dar de baja lógica con confirmación. La baja asigna `bin_status=3` y conserva datos, imagen y auditoría. Las imágenes se consultan con sesión autorizada.

El alta se presenta dentro del apartado de talleres, con secciones de datos y domicilio y un panel de fotografía con vista previa. El CP inexistente muestra un mensaje y limpia la dirección anterior; un CP incompleto también elimina los valores anteriores para no guardar una dirección desactualizada.

El catálogo está relacionado mediante `postal_states → postal_municipalities → postal_settlements`. Cada asentamiento tiene colonia y CP, y referencia a su municipio; el municipio referencia a su estado. Las columnas de texto de la importación inicial se conservan por compatibilidad.

Fuentes de referencia: [Catálogo oficial de Correos de México](https://www.correosdemexico.gob.mx/sslservicios/consultacp/CodigoPostal_Exportar.aspx) y [estructura del RFC publicada por el SAT](https://wwwmat.sat.gob.mx/cs/Satellite%3Fblobcol%3Durldata%26blobkey%3Did%26blobtable%3DMungoBlobs%26blobwhere%3D1461176322651%26ssbinary%3Dtrue).

Diagrama: [Alta de taller](diagramas/03-alta-taller/alta-taller.html).
