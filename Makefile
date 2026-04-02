.PHONY: test test-all dev check check-ci migrate migrate-new migrate-status uv-add prep

prep:
	docker compose up -d db worker
	docker compose run --rm dbmate up

test:
	docker compose up -d db
	docker compose run --rm dbmate up
	docker compose run -e TESTING=true --rm app pytest

test-all: prep
	docker compose run -e TESTING=true --rm app pytest -m ""

dev:
	uv run uvicorn app.api.main:app --reload

check:
	docker compose run --rm app ruff check --no-cache --fix .
	docker compose run --rm app ruff format --no-cache .
	docker compose run --rm app pyrefly check

check-ci:
	docker compose run --rm app ruff check --no-cache .
	docker compose run --rm app ruff format --no-cache --check .
	docker compose run --rm app pyrefly check

validate: test-all check-ci

migrate:
	docker compose run --rm dbmate up

migrate-new:
	docker compose run --rm dbmate new $(name)

migrate-status:
	docker compose run --rm dbmate status

uv-add:
	docker compose run --rm app uv add $(pkg)
