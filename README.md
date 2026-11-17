# QuimioResponde

Asistente técnico **referencial** de seguridad en laboratorios químicos para Chile: responde preguntas sobre normativa vigente con citas literales verificables y rechaza explícitamente cuando el corpus no cubre la pregunta.

![ci](https://github.com/criverap-duoc/quimioresponde/actions/workflows/ci.yml/badge.svg)

## Qué hace

1. **Responde con el artículo exacto.** Preguntas como «¿qué exige el Decreto 43 para almacenar líquidos inflamables?» se responden con citas numeradas; cada cita muestra la frase literal del artículo y el enlace a LeyChile. La verificación es determinista: si la cita no es subcadena del chunk recuperado, la respuesta no se entrega.
2. **Rechaza cuando no hay evidencia.** Si ningún fragmento del corpus trata el tema, o si la pregunta pide un dictamen de cumplimiento, la UI muestra «Sin evidencia verificable» con el motivo (`no_citations`, `unverifiable_quote`, `unknown_chunk`, `refusal_with_citations`). No se inventa normativa.
3. **Ingesta idempotente de normas.** El XML de la BCN se trocea por artículo y numeral; el hash de versión evita duplicar documentos y chunks al recargar la misma norma. Una cola acotada con reintentos manda los jobs agotados a una DLQ en memoria.

## Límites

- Resultado **referencial**: no dictamina cumplimiento ni certifica seguridad.
- Sin evidencia en el corpus → «no encontrado».
- Solo lectura sobre ChemLab en v1 (la integración llega en Fase 2; hoy no existe).
- Corpus de Fase 1: únicamente Decreto 43/2015 y Decreto 594/1999.
- Las respuestas son texto generado; las citas, en cambio, se verifican contra el texto almacenado.

## Capturas

<!-- TODO: capturas — añadir estas imágenes en docs/screenshots/ antes del despliegue.
![Chat con citas verificables](docs/screenshots/chat-citas.png)
![Cita expandida con el artículo de LeyChile](docs/screenshots/cita-expandida.png)
![Rechazo por falta de evidencia](docs/screenshots/sin-evidencia.png)
![Streaming de la respuesta](docs/screenshots/streaming.gif)
-->

Pendiente: las tres capturas y el GIF se añaden antes del despliegue.

## Cómo correr localmente

Requisitos: Python 3.12+ con uv, Node 22 con pnpm, y un Postgres con pgvector (Neon o local).

Backend (en `api/`):

    cd api
    uv sync
    copy .env.example .env      # en macOS/Linux: cp .env.example .env
    # rellenar DATABASE_URL (Postgres con pgvector) y GEMINI_API_KEY en .env
    uv run alembic upgrade head
    uv run uvicorn app.main:app --reload

Endpoints: `GET /healthz` (liveness), `GET /readyz` (base de datos y API key del LLM) y `POST /chat` (SSE con eventos `citations`, `answer`, `done` o `error`). El corpus se carga con la ingesta del backend; en Fase 1 no hay endpoint público de ingesta y el script local de carga no se versiona (`api/scripts/` está en `.gitignore`). Sin corpus cargado, `/chat` responde con un rechazo.

Frontend (en `web/`):

    cd web
    pnpm install
    copy .env.example .env      # en macOS/Linux: cp .env.example .env
    pnpm dev

Abre `http://localhost:5173`. `VITE_API_URL` apunta por defecto a `http://localhost:8000`, el origen permitido por CORS en desarrollo.

Evals (desde la raíz):

    make evals

Corre 20 casos offline (10 de recuperación, 5 de rechazo, 5 de citas) contra `evals/fixtures/retrieval_golden.json`. No usa red ni base de datos: es lo que corre CI. Para regenerar el golden, con `DATABASE_URL` apuntando a una base con la norma cargada y `GEMINI_API_KEY` en `api/.env`:

    cd evals
    uv sync
    uv run python -m harness.run --online

Verificación completa:

    make check      # ruff + mypy + tests unitarios
    make test-int   # tests de integración con Testcontainers (requiere Docker)
    make clean      # borra cachés y artefactos de build

## Arquitectura

Web React + Vite (SSE) → API FastAPI → Postgres con pgvector.

- Recuperación híbrida: vector HNSW + full-text español, fusionados con RRF.
- Verificación determinista de citas contra el texto almacenado; sin cita válida no hay respuesta.
- Gemini redacta con salida JSON validada por Pydantic; los errores del proveedor se traducen a `problem+json`.
- Ingesta idempotente por hash de versión desde el XML público de la BCN, con cola acotada y DLQ.
- Traza por respuesta en `chat_traces` (pregunta, respuesta, chunks citados).

Detalle completo en [ARCHITECTURE.md](ARCHITECTURE.md).

## Estado

Existe y funciona (Fase 1):

- API FastAPI con `/healthz`, `/readyz` y `POST /chat` en SSE, rate limit y errores `problem+json`.
- Recuperación híbrida con pgvector y `tsvector` español sobre chunks por artículo y numeral.
- Verificación determinista de citas y trazas en `chat_traces`.
- Ingesta idempotente desde el XML de LeyChile con cola acotada, reintentos y DLQ.
- Web con streaming, citas numeradas expandibles, tarjeta de rechazo, tema claro/oscuro según el sistema y esqueleto de cold start.
- 20 evals offline versionadas, tests unitarios y de integración con Testcontainers, CI en GitHub Actions.

No existe todavía:

- **Fase 2:** motor de reglas de compatibilidad en YAML, herramientas cerradas (`search_regulation`, `get_chemical_info`, `get_inventory`, `check_storage_compatibility`), agente LangGraph acotado, integración de solo lectura con ChemLab.
- **Fase 3:** evals completas con LLM real, circuit breaker con proveedor de respaldo, streaming real del SDK, uso de tokens y costo por respuesta.
- **Fase 4:** despliegue en AWS (SAM, API Gateway, Lambda, SQS + DLQ, EventBridge, S3, canary).
- No hay despliegue en Render ni en Vercel.

## Atribución

Fuente de normativa: Ley Chile – Biblioteca del Congreso Nacional. Licencia CC BY-NC-ND 4.0.

El uso de la API oficial de LeyChile y el alcance de la ingesta se documentan en [ADR-005](docs/adr/005-leychile-api.md).

## Licencia

El código de este repositorio se distribuye bajo licencia MIT. El contenido normativo citado pertenece a la Biblioteca del Congreso Nacional (CC BY-NC-ND 4.0) y no se relicencia: se comparte sin modificaciones, con atribución y sin fines comerciales.
