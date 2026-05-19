.PHONY: install dev chunks index index-all chunking-compare queries test lint format up down

install:
	uv sync --extra dev

dev:
	uv run uvicorn app.main:app --reload --app-dir backend

chunks:
	uv run python scripts/build_chunks.py --raw-dir data/raw/german-laws

index:
	uv run python scripts/build_index.py

index-all:
	uv run python scripts/build_index.py --all

chunking-compare:
	uv run python scripts/compare_chunking.py

queries:
	uv run python scripts/run_example_queries.py

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy

format:
	uv run ruff format .
	uv run ruff check . --fix

up:
	docker compose up -d

down:
	docker compose down
