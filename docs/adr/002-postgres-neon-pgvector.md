# ADR-002: PostgreSQL Neon + pgvector como DB única

## Contexto
Necesitamos vectores (768 dim), full-text en español, datos relacionales (documentos, chunks, trazas, evals) y un free tier viable.

## Decisión
PostgreSQL en Neon con pgvector. Una sola DB para todo.

## Alternativas
- Pinecone/Qdrant: servicio extra, otro free tier que gestionar, sin transacciones con datos relacionales.
- pgvector en RDS: coste y complejidad mayores para Fase 1–3.

## Consecuencias
Menos servicios, transacciones que abarcan vectores y metadatos. Riesgo: límites de almacenamiento y conexiones de Neon; se monitoriza y se documenta.