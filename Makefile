.PHONY: dev db-upgrade seed backend-test backend-lint frontend-build frontend-lint frontend-e2e test lint

dev:
	python -m uvicorn app.main:app --app-dir backend --reload

db-upgrade:
	alembic -c alembic.ini upgrade head

seed:
	python backend/seed.py

backend-test:
	python -m pytest backend/tests

backend-lint:
	python -m ruff check backend
	python -m mypy backend

frontend-build:
	npm --prefix frontend run build

frontend-lint:
	npm --prefix frontend run lint

frontend-e2e:
	npm --prefix frontend run e2e

test: backend-test

lint: backend-lint frontend-lint
