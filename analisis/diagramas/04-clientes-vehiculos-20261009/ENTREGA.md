# Entrega Archify · clientes y vehículos

Tipo de los tres diagramas: **workflow**, esquema 2, perfil showcase. Cada entrega aprobó validación 9/9, cero errores/advertencias, publicación, comprobación del artefacto y `browser-check` automático. Revisión perceptual: **no solicitada/no realizada**; los recibos sugieren inspeccionar algunas rutas con tres dobleces. Los flujos están en español; parte de los controles del visor conserva la traducción inglesa predeterminada.

| Proceso | Diagrama | Recibo actual | Correcciones de composición |
|---|---|---|---|
| UC-CV-01 Registrar cliente | [HTML](01-registrar-cliente/registrar-cliente.html) | [Resumen](01-registrar-cliente/registrar-cliente.finalize-summary.json) | 0 |
| UC-CV-02/03/04 Administrar clientes | [HTML](02-administrar-clientes/administrar-clientes.html) | [Resumen](02-administrar-clientes/administrar-clientes.finalize-summary.json) | 1: separar la ruta de error de la baja |
| UC-CV-06 Registrar vehículo | [HTML](03-registrar-vehiculo/registrar-vehiculo.html) | [Resumen vigente, revisión 2](03-registrar-vehiculo/revision-2/registrar-vehiculo.finalize-summary.json) | 1: compactar columnas manteniendo texto y flujo |

Cada resumen incluye hashes SHA-256 completos de especificación y artefacto, y las rutas de su recibo completo y evidencia automática de navegador. No se afirma una revisión visual manual.

Las copias públicas tienen hashes idénticos a los artefactos revisados:

- [Registrar cliente](http://127.0.0.1:5176/diagramas/registrar-cliente-fases.html).
- [Administrar clientes](http://127.0.0.1:5176/diagramas/gestionar-clientes.html).
- [Registrar vehículo](http://127.0.0.1:5176/diagramas/registrar-vehiculo.html).

Los diagramas anteriores se conservan en `.archify`. Los diagramas de roles y alta de taller no se modificaron.

## Revisión UC-CV-06 contra la imagen

Incluye «buscar duplicados» antes de guardar y conserva el rechazo de altas simultáneas mediante los índices únicos. Diagrama de tipo workflow, validación showcase 9/9 con cero errores y advertencias, evidencia automática de navegador aprobada, revisión perceptual no solicitada/no realizada, una corrección de composición.

- Especificación SHA-256: `470908ff54b47e9ca6123350c0a14cfa234e9de6e62f3b485fa63687cb0ea443`.
- Artefacto SHA-256: `870f3230e51c5ddd5dc5ad5b0586d4ed0801706b1eb420b7808bef995f968552`.

El resumen y la evidencia de la entrega anterior permanecen como históricos. El recibo en `revision-2` corresponde al HTML vigente.
