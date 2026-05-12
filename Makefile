.PHONY: install dev chunks test lint format up down

install:
	uv sync --extra dev

dev:
	uv run uvicorn app.main:app --reload --app-dir backend

chunks:
	uv run python scripts/build_chunks.py --raw-dir data/raw/german-laws

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
