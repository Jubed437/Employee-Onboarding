.PHONY: dev backend-test backend-lint frontend-build frontend-lint test lint

dev:
	python -m uvicorn app.main:app --app-dir backend --reload

backend-test:
	python -m pytest backend/tests

backend-lint:
	python -m ruff check backend
	python -m mypy backend

frontend-build:
	npm --prefix frontend run build

frontend-lint:
	npm --prefix frontend run lint

test: backend-test

lint: backend-lint frontend-lint
