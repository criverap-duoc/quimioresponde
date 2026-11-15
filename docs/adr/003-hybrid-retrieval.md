# ADR-003: Recuperación híbrida por artículo/numeral con RRF

## Contexto
Las citas exactas son el diferenciador. El chunking fijo por caracteres rompe artículos y pierde contexto legal. La búsqueda solo vectorial falla en términos exactos (números de decreto, nombres de sustancias).

## Decisión
Trozos por artículo/numeral con metadatos de cita. Búsqueda híbrida: vector HNSW (Gemini 768) + tsvector español, fusionados con Reciprocal Rank Fusion (RRF). Cada chunk conserva `documento`, `articulo`, `numeral`, `url`, `version_hash`.

## Alternativas
- Solo vector: peor hit@k en consultas con números o nombres exactos.
- Solo BM25: pierde paráfrasis.
- Chunking fijo: citas imprecisas.

## Consecuencias
Mejor hit@k y citas verificables. Coste: parseo fino de fuentes BCN y mantenimiento del tsvector.