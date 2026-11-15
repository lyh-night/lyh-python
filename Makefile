.PHONY: run format lint test sync

sync:
	uv sync

run:
	uv run uvicorn agent_service.main:app --reload

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

test:
	uv run pytest
