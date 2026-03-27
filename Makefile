.PHONY: test test-all dev check migrate migrate-new migrate-status uv-add

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

migrate:
	docker compose run --rm dbmate up

migrate-new:
	docker compose run --rm dbmate new $(name)

migrate-status:
	docker compose run --rm dbmate status

uv-add:
	docker compose run --rm app uv add $(pkg)
