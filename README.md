# Taller Mecánico · Autenticación y gestión de clientes

SPA para una plataforma de gestión de taller mecánico. Implementa usuarios con rol, estado y una sola sesión activa por cuenta, administración de roles, clientes y talleres y registro de vehículos asociados a clientes.

Entrega actual: [clientes, talleres y vehículos, fases y permisos](analisis/CLIENTES-VEHICULOS.md). Registrar clientes y vehículos requiere administrador/recepcionista; actualizar clientes requiere administrador/secretaria; desactivar clientes requiere administrador. El taller se selecciona en el alta y no se puede cambiar en la edición.

Consulta el [análisis actualizado de cuentas, roles y talleres](analisis/README.md). El [inventario anterior de funcionalidades](docs/ESTADO-PROYECTO.md) corresponde al 7 de octubre.

## Administración de vehículos · video del 22 de octubre

Disponible en **Administración de vehículos**: búsqueda y consulta de expedientes, edición en modal, baja lógica solo para administrador, cambio de cliente activo y galería privada. Administrador y recepcionista registran, actualizan y asocian; secretaria conserva únicamente consulta en este módulo. El alta también sigue disponible desde la tabla de clientes.

Se pueden adjuntar varias fotografías JPG/PNG/WebP de **máximo 15 MB cada una**; por seguridad se limita la galería a 10 fotos por vehículo. VIN y placa permanecen únicos aun con baja lógica. Fotos, relación y auditoría se guardan transaccionalmente, sin borrar datos existentes ni agregar un ID técnico al formulario. Consulta la [tabla de fases y verificación UC-CV-07..16](analisis/fase-administrar-vehiculos.md).

Para **modificar** desde Administración de vehículos, el VIN registrado se muestra en solo lectura. Completa placa mexicana, marca, modelo, año, versión, color y kilometraje, y conserva o agrega **al menos una fotografía**. El kilometraje `0` es válido y las fotos existentes cuentan. La API rechaza datos incompletos e intentos de cambiar el VIN. En el alta, kilometraje y fotos son opcionales.

## Tecnologías

- Frontend: Vue 3 + Vite + TypeScript estricto + Vuetify 3.
- Backend: Python + FastAPI + SQLAlchemy + MySQL.
- UC-CV-01..06 Clientes y registro de vehículos: módulo C# / .NET 10 integrado con FastAPI y MySQL, con relaciones y auditoría transaccional.

## UC-CV-01 Registrar cliente

Consulta [tabla de fases, patrones, reglas y ejecución](docs/UC-CV-01-RegistrarCliente.md). El alta de clientes está habilitada únicamente para administradores y recepcionistas e incluye confirmación, bloqueo de duplicados y auditoría transaccional. El módulo se encuentra en `customer-service`, la solución C# en `TallerMecanico.slnx` y el diagrama de fases Archify en `.archify/architecture-uc-cv-01-fases-20261007-181224`.

El directorio permite buscar y consultar con administrador/recepcionista/secretaria; actualizar con administrador/secretaria y desactivar solo con administrador. La baja es lógica y conserva historial y vehículos. La numeración actual sigue las imágenes de Fase 1: UC-CV-02 consultar, 03 actualizar, 04 desactivar, 05 duplicados, 06 vehículo. Con la app iniciada, abre [la aplicación](http://127.0.0.1:5176/) o [el diagrama de Archify](http://127.0.0.1:5176/diagramas/gestionar-clientes.html).

## Puesta en marcha paso a paso

Si esta instalación ya existe, conserva los archivos `.env` y el administrador actual; no repitas su creación. Para ejecutarla abre las tres terminales indicadas abajo y usa los puertos fijos 8002, 8003 y 5176.

1. Para una instalación nueva: instala **Node.js LTS** (incluye npm), **Python 3.11+**, MySQL 8+ y **.NET SDK 10** para el módulo de clientes.
2. Crea la base de datos ejecutando `database/schema.sql` desde MySQL Workbench o consola.
3. Solo en una instalación nueva, copia `backend/.env.example` a `backend/.env` y `frontend/.env.example` a `frontend/.env`. Actualiza `DATABASE_URL` y `SECRET_KEY`; permite el origen `http://127.0.0.1:5176`. No sobrescribas una configuración existente.
4. Desde `backend`, crea y activa un entorno virtual e instala dependencias:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

5. Crea el primer administrador. La contraseña se solicita de forma oculta y solo se guarda como hash Argon2:

   ```powershell
   python seed_admin.py
   ```

6. Terminal 1, desde `backend`: inicia la API. Las migraciones repetibles se aplican al arrancar:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002
   ```

7. Terminal 2, desde `customer-service`: inicia el módulo de clientes:

   ```powershell
   dotnet run
   ```

   Lee la configuración MySQL de `../backend/.env` y escucha en el puerto 8003.

8. Si aún no está cargado el catálogo postal, desde la raíz ejecuta `backend\.venv\Scripts\python.exe tools\importar-catalogo-postal.py`. Si ya existe, el importador lo conserva. Este equipo ya tiene el catálogo nacional cargado.

9. Terminal 3, desde `frontend`: instala los paquetes solo si hacen falta e inicia la SPA. Verifica `VITE_API_URL=http://127.0.0.1:8002` en su configuración:

   ```powershell
   npm install
   npm run dev -- --host 127.0.0.1 --port 5176 --strictPort
   ```

10. Abre `http://127.0.0.1:5176/`. Si un puerto ya está ocupado por este proyecto, reutiliza el servicio; no inicies otra copia. Con `--strictPort` no se cambia silenciosamente el puerto.

## Comportamiento de seguridad

- Las contraseñas se hashean con Argon2 y nunca se devuelven al cliente.
- El backend valida credenciales, estado activo, token JWT y sesión persistida.
- La fila de usuario se bloquea durante el login para impedir dos accesos simultáneos.
- Si existe una sesión vigente se devuelve un mensaje claro y no se crea otra.
- Cerrar sesión invalida el registro de sesión y el JWT deja de ser válido.
- El registro público desde el login crea únicamente cuentas Invitado y no recibe un rol. Solo el administrador administra roles y cuentas de personal. Alta de clientes, vehículos y talleres: administrador/recepcionista. Edición de clientes: administrador/secretaria. Baja de clientes: administrador. Invitado y Mecánico no gestionan clientes.
- La tabla `status` contiene ID, valor y descripción. `bin_status` referencia su ID: 1 activo, 2 suspendido. Eliminar un rol aplica SoftDeleted: pasa a 2 y se conserva para consulta o reactivación. Las cuentas con ese rol no pueden acceder mientras esté suspendido. El ID 3 permanece para las bajas de clientes/talleres existentes; no se alteran esos módulos.
- El alta de taller exige foto JPG, PNG o WebP de máximo 10 MB (10 000 000 bytes). CP + Enter prellena estado, municipio y colonia sin enviar el formulario. Sin CP se seleccionan estado, municipio y colonia para obtenerlo automáticamente.
- La recuperación envía un enlace de 15 minutos al correo registrado; el token se almacena como hash y se invalida tras usarlo.

## Configurar recuperación por Gmail

En `backend/.env`, completa `SMTP_PASSWORD` con una contraseña de aplicación de la cuenta indicada en `SMTP_USER`. Las demás variables Gmail son `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_FROM` y `SMTP_STARTTLS=true`. Reinicia FastAPI después de guardar. Sin esa clave el servidor devolverá 503 al solicitar recuperación, para no afirmar que se envió un correo que no salió. El correo de cada usuario se guarda al crearlo; el administrador existente puede guardar el suyo desde su panel.

> Para producción usa HTTPS, un `SECRET_KEY` aleatorio largo, una URL MySQL con cuenta de mínimos privilegios y restringe `CORS_ORIGINS`.
