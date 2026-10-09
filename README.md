# Taller Mecánico · Autenticación y gestión de clientes

SPA para una plataforma de gestión de taller mecánico. Implementa usuarios con rol, estado y una sola sesión activa por cuenta, administración de roles, clientes y talleres.

Consulta el [análisis actualizado de cuentas, roles y talleres](analisis/README.md). El [inventario anterior de funcionalidades](docs/ESTADO-PROYECTO.md) corresponde al 7 de octubre.

## Tecnologías

- Frontend: Vue 3 + Vite + TypeScript estricto + Vuetify 3.
- Backend: Python + FastAPI + SQLAlchemy + MySQL.
- UC-CV-01/02/03 Registrar, actualizar y eliminar clientes: módulo C# / .NET 10 integrado con FastAPI y MySQL.

## UC-CV-01 Registrar cliente

Consulta [tabla de fases, patrones, reglas y ejecución](docs/UC-CV-01-RegistrarCliente.md). El alta de clientes está habilitada únicamente para administradores y recepcionistas e incluye confirmación, bloqueo de duplicados y auditoría transaccional. El módulo se encuentra en `customer-service`, la solución C# en `TallerMecanico.slnx` y el diagrama de fases Archify en `.archify/architecture-uc-cv-01-fases-20261007-181224`.

El directorio permite buscar, consultar, actualizar y eliminar clientes únicamente con esos dos roles. La eliminación es lógica y conserva el historial. Consulta [UC-CV-02/03, API, pruebas y diagrama actualizado](docs/UC-CV-02-03-GestionClientes.md). Con la app iniciada, abre [la aplicación](http://127.0.0.1:5176/) o [el diagrama de Archify](http://127.0.0.1:5176/diagramas/gestionar-clientes.html).

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
- El registro público desde el login crea únicamente cuentas Invitado y no recibe un rol. Solo el administrador crea, actualiza, da de baja o asigna roles y crea cuentas de personal. Clientes y talleres requieren administrador o recepcionista; una cuenta Invitado no tiene esos permisos.
- La tabla `status` contiene ID, valor y descripción. `bin_status` referencia su ID: 1 activo, 2 suspendido. Eliminar un rol aplica SoftDeleted: pasa a 2 y se conserva para consulta o reactivación. Las cuentas con ese rol no pueden acceder mientras esté suspendido. El ID 3 permanece para las bajas de clientes/talleres existentes; no se alteran esos módulos.
- El alta de taller exige foto JPG, PNG o WebP de máximo 10 MB (10 000 000 bytes). CP + Enter prellena estado, municipio y colonia sin enviar el formulario. Sin CP se seleccionan estado, municipio y colonia para obtenerlo automáticamente.
- La recuperación envía un enlace de 15 minutos al correo registrado; el token se almacena como hash y se invalida tras usarlo.

## Configurar recuperación por Gmail

En `backend/.env`, completa `SMTP_PASSWORD` con una contraseña de aplicación de la cuenta indicada en `SMTP_USER`. Las demás variables Gmail son `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_FROM` y `SMTP_STARTTLS=true`. Reinicia FastAPI después de guardar. Sin esa clave el servidor devolverá 503 al solicitar recuperación, para no afirmar que se envió un correo que no salió. El correo de cada usuario se guarda al crearlo; el administrador existente puede guardar el suyo desde su panel.

> Para producción usa HTTPS, un `SECRET_KEY` aleatorio largo, una URL MySQL con cuenta de mínimos privilegios y restringe `CORS_ORIGINS`.
