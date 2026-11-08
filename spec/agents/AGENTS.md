# Guía del repositorio

## Estructura y arquitectura del proyecto

- `frontend/`: Vue 3, Vite, TypeScript estricto y Vuetify 3. Componentes, clientes de API y validadores en `src/components/`, `src/services/` y `src/validation/`; recursos públicos en `public/`.
- `backend/app/`: autenticación, autorización, roles, talleres y pasarela al servicio de clientes con FastAPI.
- `customer-service/`: dominio de clientes/vehículos en .NET 10, persistencia MySQL y `SelfTests.cs`. Conserva la separación entre Builder, Bridge y Strategy.
- `database/` contiene SQL; `tests/`, pruebas entre servicios y datos de prueba. `analisis/` y `docs/` contienen tablas de fases y diagramas Archify.

## Comandos de compilación, pruebas y desarrollo

Requisitos: Node.js LTS, Python 3.11+, MySQL 8+ y .NET SDK 10. Consulta `README.md` para la configuración inicial. Instala paquetes con `npm install` en `frontend/` y dependencias del backend en `backend/.venv`.

Ejecuta los servicios en terminales PowerShell independientes:

- Desde `backend/`: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002`.
- Desde `customer-service/`: `dotnet run` inicia la API de clientes en el puerto 8003; `dotnet build` la compila.
- Desde `frontend/`: `npm run dev -- --host 127.0.0.1 --port 5176 --strictPort` inicia la SPA; `npm run build` comprueba tipos y genera la compilación.

Reutiliza los servicios existentes; no cambies puertos silenciosamente.

## Estilo y nomenclatura

En TypeScript usa dos espacios, comillas simples y sin punto y coma; prefiere `<script setup lang="ts">`, PascalCase para componentes/tipos y camelCase para valores. Python: cuatro espacios y snake_case para funciones/módulos. C#: cuatro espacios y PascalCase para tipos/métodos. Mantén TypeScript estricto, comprobaciones de nulabilidad y advertencias como errores en C#. No hay scripts específicos de análisis estático/formateo. Conserva textos en español y la paleta `#FAEBD7`/`#2F4F4F`.

## Pruebas

Se usan aserciones de Node, aserciones/dobles de prueba de Python y el ejecutor propio de C#. Desde la raíz: `node tests/vehicle_identifiers.cjs` y `backend\.venv\Scripts\python.exe tests/customer_permissions.py`. Desde `customer-service/`: `dotnet run -- --self-test`; `dotnet run -- --integration-test` requiere además MySQL configurado. La integración HTTP requiere ambas API. Usa nombres descriptivos snake_case y datos JSON compartidos. Sin porcentaje mínimo configurado, cubre validaciones, duplicados, permisos, bajas lógicas y reversión de auditoría. Aísla y limpia los datos de prueba.

## Commits y solicitudes de incorporación

El historial usa resúmenes breves en español, a veces con `docs:`; no existe una convención uniforme obligatoria. Mantén commits enfocados. Cada PR debe describir cambios, enlazar incidencias/casos de uso, indicar comandos/resultados de verificación, explicar migraciones e incluir capturas para cambios visuales.

## Seguridad y conservación de datos

No incluyas `.env`, credenciales, registros ni compilaciones en commits. Conserva cuentas, sesiones y datos existentes. Mantén autorización en servidor, contraseñas con hash, bajas lógicas y escrituras transaccionales de persistencia/auditoría. Actualiza las fases cuando cambien las reglas de negocio.
