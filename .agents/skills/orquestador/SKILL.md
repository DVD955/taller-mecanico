---
name: orquestador
description: Coordina tareas del repositorio Taller Mecánico a partir de su orquestador. Úsala al invocar $orquestador o $orquestador.md, o al pedir que se revise el catálogo de especificaciones del proyecto.
---

# Orquestador de Taller Mecánico

1. Abre el [orquestador del proyecto](../../../spec/orquestador/orquestador.md) y usa su tabla de selección para identificar las guías, fases y verificaciones pertinentes.
2. Si la invocación viene sola, audita el catálogo Markdown en modo de lectura. Compara el inventario con las rutas del índice y señala enlaces rotos, documentos omitidos y guías vacías. Usa las exclusiones que define el orquestador.
3. Si la invocación va seguida de una tarea, toma ese texto como alcance. Lee la guía del repositorio, el README y las referencias de la capa o del caso de uso afectado. Distingue especificaciones vigentes, guías técnicas y evidencias históricas.
4. Realiza la tarea solicitada y aplica las verificaciones que correspondan a su alcance. Si hay diferencias entre documentación, código y pruebas, identifica cada una con su fuente.
5. Entrega los hallazgos o cambios, la evidencia comprobada y cualquier pendiente. En la auditoría del catálogo, incluye el total de documentos, la cobertura del índice y las referencias que requieran atención.
