.PHONY: dev test lint build

dev:
	docker compose up --build

test:
	cd backend && . .venv/bin/activate 2>/dev/null || true; pytest -q

lint:
	cd backend && . .venv/bin/activate 2>/dev/null || true; ruff check .
	cd frontend && npm run lint

build:
	cd frontend && npm run build
	docker compose config >/dev/null
