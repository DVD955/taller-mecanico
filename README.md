# Taller Mecánico · Autenticación y gestión de clientes

SPA de inicio de sesión para una plataforma de gestión de taller mecánico. Implementa usuarios con rol, estado y una sola sesión activa por cuenta.

Consulta el [estado actual y la tabla de funcionalidades disponibles y pendientes](docs/ESTADO-PROYECTO.md).

## Tecnologías

- Frontend: Vue 3 + Vite + TypeScript estricto + Vuetify 3.
- Backend: Python + FastAPI + SQLAlchemy + MySQL.
- UC-CV-01/02/03 Registrar, actualizar y eliminar clientes: módulo C# / .NET 10 integrado con FastAPI y MySQL.

## UC-CV-01 Registrar cliente

Consulta [tabla de fases, patrones, reglas y ejecución](docs/UC-CV-01-RegistrarCliente.md). El alta de clientes está habilitada únicamente para administradores y recepcionistas e incluye confirmación, bloqueo de duplicados y auditoría transaccional. El módulo se encuentra en `customer-service`, la solución C# en `TallerMecanico.slnx` y el diagrama de fases Archify en `.archify/architecture-uc-cv-01-fases-20261007-181224`.

El directorio permite buscar, consultar, actualizar y eliminar clientes únicamente con esos dos roles. La eliminación es lógica y conserva el historial. Consulta [UC-CV-02/03, API, pruebas y diagrama actualizado](docs/UC-CV-02-03-GestionClientes.md). Con la app iniciada, abre [la aplicación](http://127.0.0.1:5176/) o [el diagrama de Archify](http://127.0.0.1:5176/diagramas/gestionar-clientes.html).

## Puesta en marcha paso a paso

1. Instala **Node.js LTS** (incluye npm), **Python 3.11+** y MySQL 8+.
2. Crea la base de datos ejecutando `database/schema.sql` desde MySQL Workbench o consola.
3. Copia `backend/.env.example` a `backend/.env` y actualiza `DATABASE_URL`, `SECRET_KEY` y los orígenes permitidos.
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

6. En otra terminal, inicia la API:

   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

7. Desde `frontend`, instala los paquetes e inicia la SPA:

   ```powershell
   npm install
   npm run dev
   ```

8. Abre la dirección indicada por Vite (normalmente `http://localhost:5173`).

## Comportamiento de seguridad

- Las contraseñas se hashean con Argon2 y nunca se devuelven al cliente.
- El backend valida credenciales, estado activo, token JWT y sesión persistida.
- La fila de usuario se bloquea durante el login para impedir dos accesos simultáneos.
- Si existe una sesión vigente se devuelve un mensaje claro y no se crea otra.
- Cerrar sesión invalida el registro de sesión y el JWT deja de ser válido.
- El administrador puede crear cuentas de recepcionista o mecánico desde su panel. También existe registro público desde el login para esos roles; no se permiten altas de administrador. Separar roles públicos y de personal está pendiente antes de publicar.
- La recuperación envía un enlace de 15 minutos al correo registrado; el token se almacena como hash y se invalida tras usarlo.

## Configurar recuperación por Gmail

En `backend/.env`, completa `SMTP_PASSWORD` con una contraseña de aplicación de la cuenta indicada en `SMTP_USER`. Las demás variables Gmail son `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_FROM` y `SMTP_STARTTLS=true`. Reinicia FastAPI después de guardar. Sin esa clave el servidor devolverá 503 al solicitar recuperación, para no afirmar que se envió un correo que no salió. El correo de cada usuario se guarda al crearlo; el administrador existente puede guardar el suyo desde su panel.

> Para producción usa HTTPS, un `SECRET_KEY` aleatorio largo, una URL MySQL con cuenta de mínimos privilegios y restringe `CORS_ORIGINS`.
