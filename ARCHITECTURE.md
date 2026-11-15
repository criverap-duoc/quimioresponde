# ARCHITECTURE — QuimioResponde

Asistente técnico referencial de seguridad en laboratorios químicos para Chile. Responde con citas verificables a normativa y fichas de seguridad, consulta inventario de ChemLab en solo lectura y calcula compatibilidad con un motor determinista. Nunca dictamina cumplimiento ni certifica seguridad.

## Límites duros

- Solo lectura sobre ChemLab en v1. Escritura queda para Fase 5 opcional.
- El LLM no decide compatibilidad: la calcula un motor de reglas YAML versionado; el LLM solo explica y cita.
- Sin evidencia en el corpus → "no encontrado"; no se inventa.
- El corpus se trata como datos, no como instrucciones (defensa ante prompt injection).
- AWS no se afirma hasta que Fase 4 esté desplegada y verificada.

## Componentes

Web (Vercel) → SSE/JSON → API FastAPI (Render)
  ├── Retrieval híbrida: pgvector + tsvector español + RRF
  ├── LLMClient: Gemini principal / DeepSeek respaldo + circuit breaker
  ├── Motor reglas compatibilidad (YAML determinista)
  ├── Herramientas cerradas: search_regulation, get_chemical_info, get_inventory, check_storage_compatibility
  └── Agente LangGraph acotado (máx. pasos)

PostgreSQL Neon + pgvector ← Ingesta idempotente ← Cola acotada + DLQ ← BCN / PubChem caché

ChemLab .NET ← endpoint solo lectura con API key de alcance limitado

## Flujo de una consulta

1. Rate limit y validación de entrada.
2. El agente decide recuperar, consultar inventario o calcular compatibilidad.
3. Recuperación híbrida devuelve chunks por artículo con metadatos de cita.
4. Respuesta estructurada validada con Pydantic: `{answer, citations[{chunk_id, quote}], refusal_reason?}`.
5. Verificación determinista: cada `quote` debe ser subcadena del chunk citado; si falla, se rechaza.
6. Traza en `chat_traces` (herramientas, tokens, costo).
7. UI: streaming, citas numeradas, traza colapsable, tarjeta de compatibilidad con severidad y fuente.

## Modelo de datos mínimo

`documents` (fuente, norma, versión por hash, vigencia, URL), `chunks` (documento, artículo, numeral, texto, embedding 768, tsvector español), `ingest_jobs`, `eval_cases`, `eval_runs`, `chat_traces`.

## Recuperación

Trozos por artículo/numeral, no por longitud fija. Híbrida: vector HNSW + full-text español, fusión RRF. Embeddings Gemini 768.

## LLM

`LLMClient` con dos adaptadores tras circuit breaker, timeouts y reintentos con backoff. Gemini 2.5 Flash como principal (free tier con RPM/RPD limitados). DeepSeek V4-Flash como respaldo: sin free tier, pero caché de prefijo reduce coste de instrucciones estables. Se usa solo en fallback y bajo volumen.

## Resiliencia

Ingesta idempotente por hash de documento+versión (Idempotency-Key). Cola acotada con concurrencia limitada y 429 + Retry-After si se llena. DLQ con reintentos. Re-ingesta programada.

## Despliegue por fases

- Fases 1–3: Render (API) + Vercel (web), con UX para cold start.
- Fase 4: AWS SAM (API Gateway HTTP, Lambda, SQS+DLQ, EventBridge Scheduler, S3, canary con alias y CodeDeploy rollback). Neon sigue como DB. No afirmar AWS hasta verificar despliegue.

## Verificado con fuentes oficiales

- Decreto 43 (2015) y Decreto 594 (1999) vigentes y disponibles en BCN/leychile.cl en HTML/XML; base normativa inicial.
- AWS free tier 2026: Lambda 1M requests/mes, SQS 1M requests/mes, EventBridge Scheduler ~14M invocaciones/mes; suficiente para Fase 4, no se afirma hasta desplegar.
- Gemini free tier: límites por RPM/RPD variables (p. ej. 15 RPM / 1.500 RPD / 1M TPM en Flash); el diseño asume cuello de botella y prioriza evals offline.
- DeepSeek: sin free tier en API; caché de prefijo con descuento ~90–98% sobre input fresco.