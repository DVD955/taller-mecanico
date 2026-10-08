# Gestión de clientes: UC-CV-02 y UC-CV-03

Extensión de UC-CV-01 RegistrarCliente. Solo ADMINISTRADOR y RECEPCIONISTA, activos y con sesión vigente, pueden consultar, registrar, actualizar y eliminar clientes. La SPA, FastAPI y CustomerService aplican esta restricción; el servidor no acepta roles ni operadores enviados por el formulario. Un cliente u otro rol fuera de la lista permitida recibe 403. No se modifica el catálogo de roles de autenticación existente.

## TABLA FASE UC-CV-02 ActualizarCliente

| Fase | Comportamiento |
|---|---|
| Precondiciones | Sesión vigente, cuenta activa y rol permitido. Cliente existente y no dado de baja. |
| Entradas | ID y versión del cliente; nombre completo, dirección seccionada y contactos. Al menos un contacto obligatorio. |
| Validaciones | Las mismas reglas de formato y normalización del alta. Coincidencias contra otros clientes, excluyendo el propio ID; incluye clientes dados de baja. Revisión firmada ligada al operador, datos, ID y versión. |
| Ejecución | Consultar → seleccionar → capturar cambios → normalizar → buscar coincidencias → revisar y confirmar → bloquear fila y comprobar versión → actualizar cliente y claves de contacto → auditar → commit. |
| Postcondición | Mismo ID y estado, datos normalizados y versión incrementada. No se crea otro cliente. |
| Auditoría | AuditEntry con acción UC-CV-02 ActualizarCliente, operador obtenido de sesión, cliente y hora UTC. Se guarda dentro de la misma transacción. |
| Respuesta | 200 con Customer y AuditEntry; 401 sin sesión; 403 rol no permitido; 404 inexistente o eliminado; 409 duplicado o versión obsoleta; 422 datos/revisión/confirmación inválidos; 503 servicio no disponible. |

## TABLA FASE UC-CV-03 EliminarCliente

| Fase | Comportamiento |
|---|---|
| Precondiciones | Sesión vigente, cuenta activa y rol permitido. Cliente existente y no dado de baja. |
| Entradas | ID, versión y confirmación explícita. El diálogo muestra el nombre e ID exactos. |
| Validaciones | Confirmación obligatoria y versión vigente. El bloqueo de fila impide competir con una edición o segunda eliminación. |
| Ejecución | Seleccionar → mostrar consecuencias → confirmar → bloquear fila → verificar versión → marcar INACTIVO y deleted_at → incrementar versión → auditar → commit → actualizar listado. |
| Postcondición | Baja lógica: desaparece del directorio y búsquedas normales; sus datos, contactos únicos y auditorías permanecen en MySQL. No se elimina una cuenta de acceso. |
| Auditoría | AuditEntry con acción UC-CV-03 EliminarCliente, operador, cliente y hora UTC. Una segunda eliminación no agrega otra auditoría. |
| Respuesta | 200 con Customer INACTIVO y AuditEntry; 401/403/404/409/422/503 según la condición. Cancelar no cambia datos. |

## Consistencia, seguridad y patrones

- Edición y baja son transacciones: si falla la auditoría, se revierten también datos, estado, versión y claves de contacto. Las restricciones UNIQUE resuelven carreras de duplicados.
- Cada edición y baja bloquea el cliente con SELECT FOR UPDATE y compara su versión antes de escribir. Una pantalla desactualizada recibe 409 y debe volver a consultar.
- Los contactos de clientes dados de baja permanecen reservados. No hay borrado físico ni restauración pública en esta entrega; no se recrea un cliente duplicado para reemplazarlo.
- Builder reconstruye los datos editados; Strategy conserva las reglas por contacto; CustomerManagement/ManageCustomers e ICustomerManagementStore amplían el Bridge hacia MySqlCustomerStore.
- La migración aditiva agrega `version` (inicial 1) y `deleted_at` a clientes existentes. No modifica usuarios, sesiones ni los datos de clientes ya registrados.
- La auditoría registra quién, cliente, acción y cuándo. No contiene una copia de los valores anteriores; esta entrega no agrega una pantalla de auditoría o restauración.

## Interfaz

`CustomerManagement.vue` reemplaza el formulario aislado por un directorio con búsqueda por nombre, correo, teléfonos o municipio, paginación de 10 registros, estados de carga/error/vacío y consulta detallada. En escritorio usa tabla; por debajo de 760 px usa tarjetas. Conserva la paleta #FAEBD7 / #2F4F4F.

La revisión de navegador comprobó ambas presentaciones. También se ajustó el encabezado para que cierre de sesión y marca se acomoden sin desbordamiento horizontal en pantallas estrechas.

**Nuevo cliente** y **Actualizar** reutilizan `CustomerRegistration.vue`: capturar → revisar datos normalizados y coincidencias → confirmar. **Eliminar** abre un diálogo independiente con confirmación y explicación de la baja lógica. El panel solo se monta para los dos roles autorizados.

## API

| Método | Ruta FastAPI | Uso |
|---|---|---|
| GET | /api/customers?page=1&page_size=10&search= | Directorio paginado sin bajas |
| GET | /api/customers/{id} | Detalle sin bajas |
| POST | /api/customers/preview | Revisión del alta |
| POST | /api/customers | Alta confirmada |
| POST | /api/customers/{id}/preview | Revisión de edición: customer + version |
| PUT | /api/customers/{id} | Edición: customer + version + previewToken + confirmed |
| DELETE | /api/customers/{id} | Baja: cuerpo JSON con version + confirmed |

FastAPI en 8002 delega al módulo C# en 8003. CORS permite DELETE. Los comandos de arranque permanecen en [UC-CV-01](UC-CV-01-RegistrarCliente.md). Aplicación local: http://127.0.0.1:5176/.

## Comprobaciones ejecutadas

El 7 de octubre de 2026 se aprobaron **62 comprobaciones**: 16 de dominio, 8 de MySQL y 38 HTTP/MySQL. Incluyen permisos en FastAPI y acceso directo a C#, ambos operadores autorizados, búsqueda, detalle, duplicados, confirmación, datos alterados, versiones antiguas, bajas invisibles, historial conservado y sesión revocada. Ocho escrituras concurrentes de cada operación generan exactamente un cambio; fallos de auditoría revierten registro, edición y baja. Los datos de estas pruebas llevan identificadores únicos y se limpian al finalizar.

```powershell
cd 'C:\Taller Mecanico\customer-service'
dotnet run --no-build -- --self-test
dotnet run --no-build -- --integration-test
cd 'C:\Taller Mecanico\backend'
.\.venv\Scripts\python.exe -X utf8 ..\tests\customer_api_integration.py
```

## Diagrama actualizado de Archify

Vista de arquitectura de la especificación funcional: autorización, directorio, registrar, actualizar, eliminar, validaciones, confirmación, transacción y respuesta. Conserva la versión anterior en su propia carpeta; no atribuye el código modificado a un commit no existente.

- Fuente: `.archify/architecture-gestion-clientes-20261007-185014/candidate.json`.
- HTML: `.archify/architecture-gestion-clientes-20261007-185014/gestionar-clientes.html`.
- Especificación SHA256: `c79359de28587211205353eff0c20609fd88d460befbc2dd261e47c88782396b`.
- Artefacto SHA256: `ab64c36d77efe1c26bb8d58659c2c53a6a43e643197cad4a3fd40eef9cf1f641`.
- Recibo: `gestionar-clientes.finalize-summary.json`, junto al HTML; contiene la referencia a la evidencia de navegador.
- Gates validate, deliver, check y browser-check: PASS, sin diagnósticos. Revisión visual manual del diagrama: no solicitada; no se confunde con el gate automático del navegador.

Visor local: http://127.0.0.1:5176/diagramas/gestionar-clientes.html. La dirección anterior `/diagramas/registrar-cliente-fases.html` también sirve ahora el diagrama actualizado (copias con hash idéntico).

```powershell
node tools/archify/archify/bin/archify.mjs finalize architecture .archify/architecture-gestion-clientes-20261007-185014/candidate.json .archify/architecture-gestion-clientes-20261007-185014/gestionar-clientes.html --quality showcase --json
```
