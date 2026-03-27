.PHONY: test test-all dev check

test:
	docker compose run --rm app pytest

test-all:
	docker compose run --rm app pytest -m ""

dev:
	uv run uvicorn app.api.main:app --reload

check:
	docker compose run --rm app ruff check .
	docker compose run --rm app ruff format --check .
	docker compose run --rm app pyrefly check .
