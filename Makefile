.PHONY: check lint typecheck test test-int evals fmt

check: lint typecheck test

lint:
	cd api && uv run ruff check .

typecheck:
	cd api && uv run mypy src

test:
	cd api && uv run pytest -m "not integration"

test-int:
	cd api && uv run pytest -m integration

evals:
	cd evals && uv run python -m harness.run --offline

fmt:
	cd api && uv run ruff format .