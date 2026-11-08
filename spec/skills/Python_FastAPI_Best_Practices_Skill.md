# Python_FastAPI_Best_Practices_Skill.md

## Objetivo
Garantizar desarrollo de módulos FastAPI escalables, mantenibles, seguros y eficientes.

## Principios Obligatorios
- Clean Architecture
- SOLID
- DRY
- KISS
- Separation of Concerns
- Type Hints obligatorios
- Validación mediante Pydantic
- Async First cuando aplique
- Repository Pattern para acceso a datos
- Unit Of Work para transacciones complejas

## Estructura de Proyecto
```text
app/
├── api/
├── services/
├── repositories/
├── models/
├── schemas/
├── core/
├── infrastructure/
├── dependencies/
├── tests/
└── main.py
```

## Reglas FastAPI
### Endpoints
- Máximo una responsabilidad.
- No lógica de negocio en controllers.
- Toda lógica en services.

### Dependency Injection
- Utilizar Depends.
- Evitar instanciaciones directas.

### Validación
- Utilizar Pydantic.
- Validar entrada y salida.

## Base de Datos
### Reglas
- Prohibido SELECT *.
- Consultar únicamente columnas necesarias.
- Utilizar índices apropiados.
- Implementar paginación.
- Evitar N+1 Queries.
- Utilizar eager loading cuando corresponda.

### SQLAlchemy
- Usar sesiones controladas.
- Reutilizar conexiones.
- Implementar repository pattern.

### Optimización
- Revisar explain plans.
- Minimizar round trips.
- Batch operations para inserciones masivas.

## Seguridad
- JWT.
- Gestión segura de secretos.
- Variables de entorno.
- Validación de permisos.
- Sanitización de entradas.

## Logging
- Logging estructurado.
- Correlation Id.
- Auditoría de errores.

## Testing
### Cobertura mínima
- Unit Tests: 80%
- Integration Tests
- API Tests

## Convenciones IA
Cuando una IA genere código:
1. Analizar requerimiento.
2. Diseñar arquitectura.
3. Crear DTOs.
4. Crear servicios.
5. Crear repositorios.
6. Crear endpoints.
7. Crear pruebas.
8. Revisar rendimiento.
9. Revisar seguridad.
10. Entregar resultado final.

## Checklist
- [ ] SOLID
- [ ] Clean Architecture
- [ ] Validación
- [ ] Logging
- [ ] Testing
- [ ] Seguridad
- [ ] Optimización SQL
- [ ] Documentación
