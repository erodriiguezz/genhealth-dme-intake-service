API := services/api
WEB := apps/web
DB_PORT ?= 5433
export DB_PORT
export DATABASE_URL ?= postgresql://intake:intake@localhost:$(DB_PORT)/intake
TEST_DATABASE_URL ?= postgresql://intake:intake@localhost:$(DB_PORT)/intake_test

.PHONY: verify dev test migrate seed eval fmt

verify:
	docker compose up -d --wait db
	cd $(API) && uv run ruff check . && uv run ruff format --check . && TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q
	cd $(WEB) && pnpm exec tsc --noEmit && pnpm exec eslint .

dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd $(API) && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd $(WEB) && pnpm dev --port 3000) & \
	wait

test:
	cd $(API) && TEST_DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -q

migrate:
	cd $(API) && uv run alembic upgrade head

seed:
	@echo "seed: added in M2/M3"

eval:
	@echo "eval: added in M2/M3"

fmt:
	cd $(API) && uv run ruff format . && uv run ruff check --fix .
