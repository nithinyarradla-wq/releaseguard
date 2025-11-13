.PHONY: install dev run test lint migrate

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	python run.py

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=releaseguard --cov-report=term-missing

lint:
	ruff check releaseguard tests
	mypy releaseguard

format:
	ruff format releaseguard tests
	ruff check --fix releaseguard tests

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"
