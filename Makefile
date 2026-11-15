.PHONY: run format lint typecheck test sync

sync:
	uv sync

# 从 .env 读取 APP_HOST/APP_PORT（缺省 127.0.0.1:8000）
run:
	@sh -c '. ./.env 2>/dev/null; exec uv run uvicorn agent_service.main:app --reload --host "$${APP_HOST:-127.0.0.1}" --port "$${APP_PORT:-8000}"'

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest
