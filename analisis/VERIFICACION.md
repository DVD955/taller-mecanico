# Cierre de cuentas, roles y talleres

Fecha: 8 de octubre de 2026, zona America/Mexico_City. Alcance: las indicaciones escritas y los adjuntos del usuario, sin módulos adicionales.

## Procesos solicitados

| Proceso | Estado al cierre | Evidencia |
|---|---|---|
| Crear cuenta pública como Invitado, sin selector de rol | Implementado y probado | UI y HTTP; inyección de `role` rechazada. |
| Crear/asignar roles únicamente como administrador | Implementado y probado | Recepcionista e Invitado reciben 403. |
| Crear rol separado de Administrar roles | Implementado y probado | Apartado propio con formulario, roles de referencia y aviso de duplicados. La administración mantiene actualización, baja y asignación. |
| Actualizar y dar de baja lógica roles | Corregido y probado | Nombre y datos editables. SoftDeleted cambia Activo (1) a Suspendido (2); conserva registro y asociaciones. Puede reactivarse sin recrearlo; su acceso queda bloqueado mientras está suspendido. |
| Tabla propia de estatus e ID en bin_status | Migrado y probado | `status(id, valor, descripcion)`: 1 activo, 2 suspendido. Roles almacena el ID y consulta el valor mediante INNER JOIN. El 3 se conserva para otros módulos, sin modificar sus bajas. |
| Alta/administración de taller por administrador o recepcionista | Implementado y probado | Consultar, registrar, actualizar y dar de baja; auditoría. |
| Taller único y RFC con expresión regular | Implementado y probado | Restricciones únicas, normalización, regex y fecha válida; no consulta inscripción SAT. |
| Fotografía de hasta 10 MB | Corregido y probado | Obligatoria en alta; formato real JPG/PNG/WebP. Se admiten 10 000 000 bytes y se rechaza un byte más, en ambas capas. |
| CP + Enter → estado, municipio y colonia | Corregido y probado | Enter prellena los tres campos sin enviar el formulario; 06600 y 97130. Si hay varias colonias se avisa y permite cambiarla. CP inexistente/incompleto limpia la dirección anterior. |
| Estado, municipio y colonia → CP | Implementado y probado | Selección en pantalla devuelve el CP del asentamiento. |
| Módulo de clientes y administración de clientes | Conservado y probado | 38 comprobaciones HTTP/MySQL y 16 de dominio. |
| Tablas de fase y tres diagramas dentro de analisis | Guardado y validado | Tres Markdown y tres HTML generados por Archify. |

## Pruebas ejecutadas

- `tests/accounts_roles_workshops_integration.py`: **66** comprobaciones de API/MySQL y validación de imagen. Incluye suspensión, reactivación y rechazo de acceso de cuentas asociadas. Informe: [verificacion-integracion.json](verificacion-integracion.json).
- `tests/customer_api_integration.py`: **38** comprobaciones HTTP/MySQL aprobadas.
- `CustomerService.dll --self-test`: **16** comprobaciones de dominio aprobadas.
- `tests/ui_accounts_roles_workshops.cjs`: **30** comprobaciones reales de navegador aprobadas. Incluye renombrar, suspender, filtrar y reactivar roles; CP + Enter; foto en el límite de 10 MB; alta y actualización de taller; escritorio y móvil. Informe: [verificacion-interfaz.json](verificacion-interfaz.json).
- `npm run build`: TypeScript estricto y Vite aprobados. El módulo C# compiló sin errores ni advertencias en la implementación de esta fase.

Total: **150 comprobaciones**, sin sumar las validaciones de diagramas como si fueran pruebas de la aplicación. Este total corresponde a las comprobaciones de estos scripts, no a todas las variantes posibles del sistema. No se realizaron envíos SMTP ni pruebas de despliegue en producción.

Las cuentas y registros de las pruebas son temporales y están identificados por UUID; la limpieza se limita a sus IDs. No se cambiaron credenciales ni sesiones reales.

Las capturas de interfaz están en `analisis/referencias/interfaz-*.png`. Se conserva la paleta y distribución del proyecto. Los diagramas 2 y 3 se actualizaron con las reglas nuevas y los tres se validaron de nuevo. Son descripciones de los procesos solicitados, no un diagrama respaldado por una revisión Git de los cambios sin confirmar.

## Recibos Archify

Archify Diagram Viewer está instalado en VS Code y recomendado en `.vscode/extensions.json`. Los tres diagramas son `workflow`, perfil `showcase`, con validación 9/9, cero errores, cero advertencias y `browser_evidence: passed`. Las copias servidas por Vite respondieron HTTP 200 y sus bytes coinciden con los HTML validados.

### 1. Crear roles

- HTML: `C:\Taller Mecanico\analisis\diagramas\01-crear-roles\crear-roles.html`.
- [Recibo automático actual](diagramas/01-crear-roles/revision-reglas/crear-roles.finalize-summary.json).
- Specification SHA-256: `e2586f4dcbb00d22f30375647bc46379d36efefd499324e085da696a5ef8e151`.
- Artifact SHA-256: `4cde2ee9444a04a854ed3ce778837536cdcea8170ffa8171b0df1f5a4a012f8e`.
- `visual_review: not_requested`; `correction_rounds: 0`.

### 2. Administrar roles

- HTML: `C:\Taller Mecanico\analisis\diagramas\02-administrar-roles\administrar-roles.html`.
- [Recibo automático actual](diagramas/02-administrar-roles/revision-reglas/administrar-roles.finalize-summary.json).
- Specification SHA-256: `4b5bb2b137789c5490e811b0b0db0ebf449d0de1bf579c90bc519257ae94df9a`.
- Artifact SHA-256: `355416ed466e00c08d675a54aec66b99be2874de8696ea44199d1829507f0b7b`.
- `visual_review: not_requested`; `correction_rounds: 0`.

### 3. Alta de taller

- HTML: `C:\Taller Mecanico\analisis\diagramas\03-alta-taller\alta-taller.html`.
- [Recibo automático actual](diagramas/03-alta-taller/revision-reglas/alta-taller.finalize-summary.json).
- Specification SHA-256: `4f078de6b5dc8eb2eaa29fdcbc55025e28ce646e57e84402afb68da7bfcbd84c`.
- Artifact SHA-256: `fceef052f470d724afb5223c1d1c3d43150bc658453970f57b01879cec5bad5a`.
- `visual_review: not_requested`; `correction_rounds: 0`. No se afirma una nueva revisión visual manual del HTML actualizado.

Los recibos y capturas anteriores se conservan como evidencia de sus versiones previas; no se reutilizan para declarar revisión visual de las nuevas versiones. Los tres recibos actuales registran `browser_evidence: passed`, `visual_review: not_requested` y `correction_rounds: 0`. Las rutas con tres curvas son sugerencias de composición del generador, no errores de validación.

## Ejecución local verificada

- SPA: `http://127.0.0.1:5176/`.
- FastAPI: `http://127.0.0.1:8002/api/health`.
- Módulo de clientes: `http://127.0.0.1:8003/health`.
- MySQL80 en ejecución.

Los tres servicios HTTP respondieron 200. Las instrucciones de arranque están en el README del proyecto. Los cambios están guardados como archivos locales; este cierre no constituye una nueva versión Git ni un respaldo de MySQL.
