# QuimioResponde

Asistente técnico **referencial** de seguridad en laboratorios químicos para Chile. Responde con citas verificables a normativa y fichas de seguridad, consulta inventario de ChemLab en solo lectura y calcula compatibilidad con un motor determinista.

**Estado: Fase 0 (cimientos).** No hay despliegue ni CI con badges todavía. Lo que aparece aquí existe; lo que no está, no está.

## Límites

- No dictamina cumplimiento ni certifica seguridad.
- Sin evidencia en el corpus → "no encontrado".
- Solo lectura sobre ChemLab en v1.

## Desarrollo

Requisitos: Python 3.12+ con uv, Node 22 con pnpm.

Backend:

    cd api
    uv sync
    uv run ruff check .
    uv run mypy src
    uv run pytest -m "not integration"

Frontend:

    cd web
    pnpm install
    pnpm lint
    pnpm build

Desde la raíz:

    make check