# ADR-004: Motor de compatibilidad determinista, separado del LLM

## Contexto
La compatibilidad química es una decisión de seguridad. Un LLM puede alucinar una incompatibilidad o omitir una crítica. El producto es referencial, pero incluso así el cálculo debe ser reproducible y auditable.

## Decisión
Motor de reglas en YAML versionado, con fuente por regla, probado con tests de tabla. El LLM nunca decide compatibilidad; solo explica el resultado y cita la fuente de la regla.

## Alternativas
- LLM decide compatibilidad: no reproducible, no auditable, riesgo alto.
- Base de datos de pares: menos legible y versionable que YAML con tests.

## Consecuencias
Resultados reproducibles y testeables. Coste: mantener la tabla de reglas y sus fuentes. El LLM queda acotado a explicar y citar.