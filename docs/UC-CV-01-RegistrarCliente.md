# TABLA FASE UC-CV-01 RegistrarCliente

Esta alta se conserva. La edición, baja lógica, directorio y diagrama que integra los tres casos de uso están documentados en [UC-CV-02/03 Gestión de clientes](UC-CV-02-03-GestionClientes.md).

| Fase | Especificación y comportamiento |
|---|---|
| Precondiciones | Usuario autenticado, activo y con sesión vigente. Rol ADMINISTRADOR o RECEPCIONISTA. MySQL y el módulo CustomerService disponibles. MECANICO recibe 403; sin sesión vigente se responde 401. |
| Entradas | Nombre completo; dirección seccionada en calle, número, colonia, municipio y estado; contactos correo, celular y teléfono alternativo. Al menos un contacto es obligatorio. La identidad del operador se obtiene de su sesión, nunca del formulario. |
| Validaciones | Campos obligatorios y límites de longitud; nombre con letras y signos usuales; correo con formato válido; teléfonos de 10 dígitos nacionales o formato internacional. Normalización de espacios, correo a minúsculas y teléfonos a formato +país. Coincidencias por correo, cualquier teléfono compartido o nombre y dirección completa normalizados. Los clientes inactivos también participan en la búsqueda. Si hay coincidencia se alerta y se bloquea el alta. |
| Ejecución | Abrir alta → capturar → validar y normalizar → buscar coincidencias → revisar y confirmar → construir Customer con Builder → persistir mediante Bridge → auditar → commit. Strategy selecciona las reglas de cada contacto. Antes de persistir se vuelve a buscar; restricciones UNIQUE protegen las solicitudes concurrentes. |
| Postcondición | Customer persistido con estado ACTIVO y un ID asignado. Sus contactos normalizados quedan reservados. Cliente, claves de contacto y auditoría existen juntos o ninguno existe. |
| Auditoría | AuditEntry (audityEntry en la solicitud): ID del operador, usuario del operador, ID del cliente, acción UC-CV-01 RegistrarCliente y hora UTC con precisión de microsegundos. Se inserta dentro de la misma transacción MySQL del cliente. Si falla, rollback de toda el alta. |
| Respuesta | Revisión: 200 con datos normalizados y coincidencias. Alta exitosa: 201 con Customer y AuditEntry. 401 sesión inválida; 403 rol no permitido; 409 duplicado; 422 datos inválidos, confirmación ausente o revisión alterada/expirada; 503 servicio no disponible. Los errores no exponen SQL ni credenciales. |

## Decisiones del caso de uso

- El contacto alternativo se interpreta como teléfono alternativo. El formulario lo nombra explícitamente.
- Números sin prefijo de exactamente 10 dígitos se interpretan como teléfonos mexicanos (+52); otros países requieren prefijo internacional. No se verifica titularidad ni existencia del teléfono/correo.
- Compartir un contacto bloquea el alta y requiere revisar el cliente existente. No existe una opción de ignorar duplicados.
- Para el nombre y la dirección se ignoran acentos y mayúsculas en la clave de coincidencia, conservando los datos visibles. No es búsqueda difusa; abreviaturas distintas pueden requerir revisión humana.
- La revisión devuelve un token firmado, ligado al operador y a todos los datos normalizados. Caduca en 10 minutos y al reiniciar CustomerService. Modificar datos exige otra revisión.
- Los permisos se comprueban en la interfaz, FastAPI, el servicio C# y el caso de uso. C# consulta `/api/auth/me` para validar JWT y la sesión persistida; no confía en un rol enviado por el navegador.

## Patrones y archivos

| Patrón | Participantes | Aplicación |
|---|---|---|
| Builder | CustomerBuilder, Customer | Construcción progresiva con WithName, WithAddress y WithContacts. Build exige objeto completo y asigna ACTIVO. |
| Bridge | CustomerRegistry, RegisterCustomer, ICustomerStore, MySqlCustomerStore | La abstracción de clientes y su caso de uso delegan persistencia al implementor. Se puede cambiar almacenamiento sin cambiar reglas de negocio. Las pruebas usan un implementor en memoria. |
| Strategy | IContactStrategy, EmailStrategy, PhoneStrategy, ContactNormalizer | Validación y normalización intercambiables por tipo de contacto, inyectadas en el constructor. |

## Integración y ejecución local

La SPA Vue permanece conectada a FastAPI en 8002. `/api/customers/preview` y `/api/customers` delegan al módulo C# en 8003. C# utiliza MySqlConnector y la misma base de datos existente. Este módulo amplía el stack original con C# porque se solicita expresamente para este caso de uso.

1. Desde la raíz, restaurar y compilar:

   ```powershell
   dotnet restore .\customer-service\CustomerService.csproj
   dotnet build .\customer-service\CustomerService.csproj --no-restore
   ```

2. Iniciar cada servicio en una terminal separada:

   ```powershell
   cd 'C:\Taller Mecanico\backend'
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
   ```

   ```powershell
   cd 'C:\Taller Mecanico\customer-service'
   dotnet run --no-build --project CustomerService.csproj
   ```

   ```powershell
   cd 'C:\Taller Mecanico\frontend'
   npm.cmd run dev -- --host 127.0.0.1 --port 5176 --strictPort
   ```

3. Abrir http://127.0.0.1:5176/, iniciar sesión como administrador o recepcionista y pulsar **Registrar cliente**. Capturar → revisar → confirmar. Los mecánicos no tienen acceso al formulario.

El módulo lee DATABASE_URL de `backend/.env` sin mostrar contraseñas. Se puede configurar `BACKEND_ENV`, `CUSTOMERS_MYSQL` (cadena de conexión .NET) y `AUTH_API_URL`. La migración `database/customers.sql` se aplica al iniciar; crea las tablas de clientes y añade las columnas de versión y baja lógica si faltan. Conserva usuarios, sesiones y clientes existentes.

## Comprobaciones reproducibles

```powershell
cd 'C:\Taller Mecanico\customer-service'
dotnet run --no-build -- --self-test
dotnet run --no-build -- --integration-test
```

La prueba de integración requiere MySQL y un administrador activo; crea datos con correos únicos de prueba y elimina exclusivamente esos registros al finalizar. Verifica ocho altas concurrentes, una única auditoría y rollback cuando falla la auditoría.

Con los tres servicios iniciados, también se puede verificar la integración HTTP:

```powershell
cd 'C:\Taller Mecanico\backend'
.\.venv\Scripts\python.exe -X utf8 ..\tests\customer_api_integration.py
```

Resultados obtenidos durante la implementación: 15 comprobaciones de dominio, 3 comprobaciones MySQL y 14 comprobaciones HTTP/MySQL aprobadas (32 en total). C# compiló con cero errores y cero advertencias; TypeScript estricto y el build de Vite finalizaron correctamente. La prueba HTTP valida la pasarela FastAPI y el servicio C#; no automatiza clics en la interfaz Vue.

## Archify

Archify 3.0.1 está disponible localmente en `tools/archify` (revisión `73aaa0696e8f72c232ea710e6fa94fd953f3e773`) y el visor **Archify Diagram Viewer 0.5.1** (`root-at-skic.archify-vscode-ext`) está instalado en Visual Studio Code. El diagrama de fases corresponde a esta especificación del caso de uso, sin atribuir referencias a un commit del código. [Archify oficial](https://github.com/tt-a1i/archify) y [visor de VS Code](https://marketplace.visualstudio.com/items?itemName=root-at-skic.archify-vscode-ext).

Fuente editable y diagrama de fases: `.archify/architecture-uc-cv-01-fases-20261007-181224/`. Es una vista de arquitectura de las responsabilidades de las siete fases. Abrir `candidate.json` desde VS Code y usar **Archify: Render to HTML File…** o el botón de vista previa. El HTML también se abre directamente en el navegador.

El borrador adicional de flujo en `.archify/workflow-uc-cv-01-20261007-181224/` se conserva con sus diagnósticos, pero no se entrega como diagrama validado: el renderer workflow rechazó la ruta de acceso denegado después de las correcciones. La vista de fases es el artefacto de entrega; las flechas muestran que auditoría y commit preceden a la postcondición, aunque la tabla enumera Postcondición antes de Auditoría.

Para generar y verificar nuevamente desde la raíz:

```powershell
node tools/archify/archify/bin/archify.mjs finalize architecture .archify/architecture-uc-cv-01-fases-20261007-181224/candidate.json .archify/architecture-uc-cv-01-fases-20261007-181224/registrar-cliente-fases.html --quality showcase --json
```

Las evidencias de generación, validación y navegador se conservan junto al diagrama. La revisión visual manual se reporta separadamente de las verificaciones automáticas.

Para reproducir la instalación de Archify en otra copia de la solución, ejecutar `tools/install-archify.ps1`. El renderer descargado se excluye de Git; el script, las fuentes JSON y los artefactos del diagrama sí forman parte del proyecto.
