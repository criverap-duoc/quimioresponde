# ADR-001: Monorepo Python + React

## Contexto
Portafolio consistente con AquaMetric (FastAPI, SQLAlchemy async, Pydantic v2, uv, ruff, mypy, React 19 + Vite + Tailwind). Un solo desarrollador, free tier, necesidad de CI único y contratos claros entre API y web.

## Decisión
Monorepo con `/api` (Python), `/web` (React), `/infra`, `/evals`, `/docs`. Contrato OpenAPI genera tipos del frontend.

## Alternativas
- Repos separados: más overhead de CI y versionado para un solo dev.
- NestJS/Django: rompe consistencia con el portafolio existente.

## Consecuencias
Un solo CI, acoplamiento controlado por OpenAPI. Riesgo: el repo crece; se mitiga con límites de líneas y recetas de "encoger".