.PHONY: up down logs migrate seed test lint fmt

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose exec backend python -m app.db.bootstrap --seed

test:
	docker compose exec backend pytest -q

lint:
	docker compose exec backend ruff check app tests migrations

fmt:
	docker compose exec backend ruff format app tests migrations
