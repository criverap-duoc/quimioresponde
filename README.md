# QuimioResponde

Asistente técnico **referencial** de seguridad en laboratorios químicos para Chile. Responde con citas verificables a normativa y fichas de seguridad, consulta inventario de ChemLab en solo lectura y calcula compatibilidad con un motor determinista.

**Estado: Fase 1 en curso (esquema de datos y configuración; todavía sin endpoints).** No hay despliegue. Lo que aparece aquí existe; lo que no está, no está.

## Límites

- No dictamina cumplimiento ni certifica seguridad.
- Sin evidencia en el corpus → "no encontrado".
- Solo lectura sobre ChemLab en v1.

## Desarrollo

Requisitos: Python 3.12+ con uv, Node 22 con pnpm.

Backend:

    cd api
    uv sync
    cp .env.example .env
    uv run alembic upgrade head
    uv run ruff check .
    uv run mypy src
    uv run pytest -m "not integration"

`alembic upgrade head` necesita `DATABASE_URL` (Postgres con pgvector) en `api/.env`; `.env` no se versiona.

Frontend:

    cd web
    pnpm install
    pnpm lint
    pnpm build

Desde la raíz:

    make check