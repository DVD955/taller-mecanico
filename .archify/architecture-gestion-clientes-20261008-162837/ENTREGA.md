# Diagrama Archify · Gestión de clientes

Generado el 8 de octubre de 2026. Vista de arquitectura de las responsabilidades y fases de UC-CV-01 Registrar, UC-CV-02 Actualizar y UC-CV-03 EliminarCliente.

Incluye sesión y permisos, directorio, captura, validación y normalización, coincidencias, confirmación, persistencia, auditoría y respuesta. Refleja la eliminación lógica y los patrones Builder, Bridge y Strategy. Los clientes del taller son registros; el catálogo de cuentas todavía no contiene el rol CLIENTE.

## Archivos y verificación

- Archivo HTML: `C:/Taller Mecanico/.archify/architecture-gestion-clientes-20261008-162837/gestionar-clientes.html`.
- Fuente editable: [candidate.json](candidate.json).
- Visor: http://127.0.0.1:5176/diagramas/gestionar-clientes.html (respuesta HTTP 200 comprobada).
- Recibo de generación: [gestionar-clientes.finalize-summary.json](gestionar-clientes.finalize-summary.json).
- Evidencia automática de navegador: [gestionar-clientes.browser-check.json](gestionar-clientes.browser-check.json).
- Capturas: [hoja de contacto](visual-check/gestionar-clientes.visual-check.html).

```text
diagram_type: architecture
output: C:/Taller Mecanico/.archify/architecture-gestion-clientes-20261008-162837/gestionar-clientes.html
specification_sha256: 506315be8905830a4cf72b7aa28610f47f5e259ef9a7d74c49cd33246afd8c52
artifact_sha256: 8de238ba52c2e7a6d87e1ff01d47fbc797946c8e213f8b0461f359a5b2badf8b
validation: showcase passed; validate, deliver, check y browser-check aprobados; 0 diagnósticos
browser_evidence: passed
visual_review: passed (gráfico visible en cuatro capturas)
correction_rounds: 0
```

La inspección visual cubrió las capturas claras y oscuras de 1440×900 y 2048×1320. Las relaciones y los nodos del gráfico se distinguen sin solapamientos visibles. A 1440×900 se requiere desplazamiento vertical para ver la parte inferior, permitido por el visor; a 2048×1320 se ve el gráfico completo. Las tarjetas explicativas continúan más abajo. No se realizaron pruebas manuales de todas las herramientas interactivas de exportación o búsqueda.

El estado `visualReview: not-requested` del finalizador corresponde exclusivamente a sus verificaciones automáticas. Esta inspección posterior de las imágenes se registra aquí por separado, sin modificar las evidencias generadas.

La copia de `frontend/public/diagramas/gestionar-clientes.html` conserva exactamente el SHA256 del HTML verificado. Las versiones anteriores del diagrama permanecen en sus carpetas respectivas.
