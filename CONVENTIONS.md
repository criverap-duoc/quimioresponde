# CONVENTIONS — QuimioResponde

## Ramas y commits

`main` es la rama de integración (sin branch protection en Fase 1–3, ver más abajo). Ramas `feat/…`, `fix/…`, `chore/…`. Commits convencionales (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`). Un commit por receta, solo si hay cambios de código o configuración; nunca commits vacíos ni prompts individuales de commit. El commit incluye el cambio y, si aplica, la actualización de docs.

## Branch protection

Durante Fase 1–3, `main` no tiene branch protection porque el proyecto es unipersonal. A partir de Fase 4 (despliegue AWS), activar branch protection y exigir PR + CI verde para mergear.

## Python (api, evals)

- `uv` para dependencias. `ruff` lint + format. `mypy --strict` en `api`.
- Pydantic v2 para esquemas; SQLAlchemy 2.0 async; Alembic para migraciones.
- Errores en `problem+json`. Excepciones tipadas; sin `except Exception` genéricos salvo en bordes delgados.
- Tests con `pytest` + Testcontainers (imagen con pgvector).
- Docstrings solo en API pública; sin comentarios que repitan el código.

## Frontend (web)

- Tipos y cliente generados desde OpenAPI (`openapi-typescript`). Wrapper mínimo con TanStack Query.
- shadcn/ui solo cuando se use. Tailwind con variables CSS para tokens.
- Una sola familia sans moderna; contraste AA; peligro/advertencia con icono + texto, no solo color.

## Límites

Archivos ≤ 300 líneas, funciones ≤ 40, complejidad ciclomática ≤ 10 (`ruff C901`). Duplicación < 3 % (`jscpd`). Código muerto detectado con `vulture`.

## Secretos

Solo en variables de entorno. Jamás en README, issues, capturas ni código. `.env` nunca se commitea (está en `.gitignore`). `.env.example` sí se versiona, con las claves documentadas y los valores vacíos.

## Documentación

ADRs cortos en `/docs/adr`. README honesto: lo que existe, lo que está planeado y lo que no. Sin badges de workflows inexistentes.

## Evals

Casos en `/evals/cases`, fixtures en `/evals/fixtures`, reportes versionados en `/evals/reports`. En CI: evals offline con fixtures. LLM real solo manual o nocturno sobre subconjunto pequeño.