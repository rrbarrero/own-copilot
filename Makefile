.PHONY: test test-all test-no-e2e test-e2e dev check check-ci migrate migrate-new migrate-status uv-add prep prep-e2e validate

prep:
	docker compose up -d db
	docker compose run --rm dbmate up

prep-e2e:
	docker compose up -d db worker
	docker compose run --rm dbmate up

test:
	docker compose up -d db
	docker compose run --rm dbmate up
	docker compose run -e TESTING=true --rm app pytest

test-no-e2e: prep
	docker compose stop worker || true
	docker compose run -e TESTING=true --rm app pytest -m "not e2e"

test-e2e: prep-e2e
	docker compose run -e TESTING=true --rm app pytest -m e2e

test-all: prep-e2e
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

validate: check test-no-e2e test-e2e

migrate:
	docker compose run --rm dbmate up

migrate-new:
	docker compose run --rm dbmate new $(name)

migrate-status:
	docker compose run --rm dbmate status

uv-add:
	docker compose run --rm app uv add $(pkg)
