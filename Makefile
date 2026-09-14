SHELL := /bin/bash
PY := uv run --frozen python
WEB := bash scripts/node.sh npm --prefix apps/web

.PHONY: setup dev build start lint typecheck test test-e2e verify-spec contracts backup

setup:
	python3 scripts/setup.py

dev:
	$(PY) scripts/launch.py dev

build:
	$(WEB) run build

start:
	$(PY) scripts/launch.py start

lint:
	uv run --frozen ruff check .
	$(WEB) run lint

typecheck:
	uv run --frozen mypy
	$(WEB) run typecheck

test:
	uv run --frozen pytest
	$(WEB) run test

test-e2e:
	$(WEB) run test:e2e

verify-spec:
	$(PY) scripts/verify_spec.py

contracts:
	$(PY) scripts/generate_contracts.py

backup:
	$(PY) scripts/backup.py
