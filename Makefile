.PHONY: test test-all dev check

test:
	uv run pytest

test-all:
	uv run pytest -m ""

dev:
	uv run uvicorn app.api.main:app --reload

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run pyrefly check .
