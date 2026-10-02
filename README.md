# Taller Mecánico · Módulo de autenticación

SPA de inicio de sesión para una plataforma de gestión de taller mecánico. Implementa usuarios con rol, estado y una sola sesión activa por cuenta.

## Tecnologías

- Frontend: Vue 3 + Vite + TypeScript estricto + Vuetify 3.
- Backend: Python + FastAPI + SQLAlchemy + MySQL.

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

> Para producción usa HTTPS, un `SECRET_KEY` aleatorio largo, una URL MySQL con cuenta de mínimos privilegios y restringe `CORS_ORIGINS`.
