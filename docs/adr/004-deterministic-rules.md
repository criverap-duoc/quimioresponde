# ADR-004: Motor de compatibilidad determinista, separado del LLM

## Contexto
La compatibilidad química es una decisión de seguridad. Un LLM puede alucinar una incompatibilidad o omitir una crítica. El producto es referencial, pero incluso así el cálculo debe ser reproducible y auditable.

## Decisión
Motor de reglas en YAML versionado, con fuente por regla, probado con tests de tabla. El LLM nunca decide compatibilidad; solo explica el resultado y cita la fuente de la regla.

Implementación R2.1: `api/src/app/rules/` carga las matrices con PyYAML 6 (ya presente en el lock como dependencia transitiva, ahora declarado directo). Precedencia: D.S. 43/2015 (Art. 17) > OSHA/NFPA 400 > `UNKNOWN`. La matriz del Art. 17 se publica en LeyChile como imagen JPEG (`dto43-p12-1.jpeg`), no como texto; la transcripción y su alcance quedan documentados en el propio YAML.

## Alternativas
- LLM decide compatibilidad: no reproducible, no auditable, riesgo alto.
- Base de datos de pares: menos legible y versionable que YAML con tests.

## Consecuencias
Resultados reproducibles y testeables. Coste: mantener la tabla de reglas y sus fuentes. El LLM queda acotado a explicar y citar.