.PHONY: up down logs migrate seed test lint shell

up: ## Arranca todos los servicios
	docker compose up -d

down: ## Para los servicios
	docker compose down

logs: ## Sigue logs de la API y el worker
	docker compose logs -f api worker

migrate: ## Aplica migraciones de Alembic
	docker compose exec api alembic upgrade head

makemigration: ## Crea nueva migración (uso: make makemigration m="add users")
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed: ## Carga datos iniciales
	docker compose exec api python -m app.scripts.seed

test: ## Tests del backend
	docker compose exec api pytest -v

lint: ## Ruff + black check
	docker compose exec api ruff check app
	docker compose exec api black --check app

shell: ## Shell IPython dentro del contenedor
	docker compose exec api ipython