.PHONY: up down build logs migrate revision seed test shell-backend

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec backend python scripts/seed_synthetic_data.py

test:
	docker compose exec backend pytest

shell-backend:
	docker compose exec backend bash
