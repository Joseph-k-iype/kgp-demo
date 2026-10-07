.PHONY: up down install migrate seed index api web dev test test-e2e verify
up:
	docker compose up -d --wait
install:
	uv sync --project backend --python 3.12
	npm ci --prefix frontend
migrate:
	PYTHONPATH=backend uv run --project backend alembic -c backend/alembic.ini upgrade head
seed: migrate
	PYTHONPATH=backend uv run --project backend python -m app.seed
	PYTHONPATH=backend uv run --project backend python -c 'from app.ontology.service import sync_ontology; print(sync_ontology())'
index:
	PYTHONPATH=backend uv run --project backend python -c 'from app.retrieval.service import index_assets; print(index_assets([]))'
api:
	PYTHONPATH=backend uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 58123
web:
	npm --prefix frontend run dev
dev:
	./scripts/dev.sh
test:
	uv run --project backend pytest backend/tests -q
test-e2e:
	npm --prefix frontend run test:e2e
verify:
	./scripts/verify.sh
down:
	docker compose down
