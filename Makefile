.PHONY: up down logs seed test lint fmt

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

seed:
	docker compose exec backend python -m app.db.bootstrap --seed

test:
	docker compose exec backend pytest -q

lint:
	docker compose exec backend ruff check app

fmt:
	docker compose exec backend ruff format app
