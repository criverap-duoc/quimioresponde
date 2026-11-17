.PHONY: check lint typecheck test test-int evals fmt clean

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

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['api/.pytest_cache', 'api/.mypy_cache', 'api/.ruff_cache', 'api/__pycache__', 'web/dist', 'web/node_modules/.vite']]"
