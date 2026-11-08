---

name: FastAPI Documentation Best Practices
description: Buenas prácticas para documentar APIs en FastAPI utilizando OpenAPI, Swagger UI y las herramientas de documentación integradas.
version: 1.0.0
language: es
--- 
## 1. Objetivo

Documentar correctamente los endpoints de FastAPI para facilitar su comprensión, uso y mantenimiento.

## 2. Buenas Prácticas

### Documentación de Endpoints

- Utilizar summary para resumir cada endpoint.
- Utilizar description para explicar su funcionamiento.
- Agrupar endpoints mediante tags.
- Definir códigos HTTP con status_code.
- Documentar respuestas adicionales con responses.

### Parámetros y Respuestas

- Utilizar Path para describir parámetros de ruta.
- Utilizar Query para documentar parámetros de consulta.
- Utilizar Body para describir datos de entrada.
- Utilizar Field para documentar campos de modelos Pydantic.
- Utilizar response_model para definir las respuestas.

### OpenAPI y Swagger

- Aprovechar la documentación automática de FastAPI.
- Configurar title, description y version.
- Agregar ejemplos cuando sea necesario.
- Revisar la documentación en Swagger UI (/docs).
- Verificar la documentación en ReDoc (/redoc).

### Funciones

- Utilizar docstrings para explicar funciones importantes.
- Documentar parámetros y valores de retorno.
- Evitar comentarios innecesarios.

### Mantenimiento

- Mantener las descripciones actualizadas.
- Verificar que los ejemplos sean correctos.
- Documentar los errores y códigos HTTP.
- Evitar información repetida.

## 3. Reglas Generales

- Utilizar las herramientas integradas de FastAPI.
- Escribir descripciones claras y cortas.
- Documentar únicamente endpoints existentes.
- No inventar parámetros ni respuestas.
- No incluir información sensible.
- No modificar funcionalidades al documentar.
- Mantener la documentación sincronizada con el código.