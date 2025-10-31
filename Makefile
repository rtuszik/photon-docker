PHOTON_VERSION := $(shell cat .last_release | tr -d '[:space:]')

.PHONY: help check lint format typecheck deadcode rebuild clean

help:
	@echo "Available targets:"
	@echo "  make check      - Run all quality checks (lint, format, typecheck, deadcode)"
	@echo "  make lint       - Run ruff linter with auto-fix"
	@echo "  make format     - Run ruff formatter"
	@echo "  make typecheck  - Run ty type checker"
	@echo "  make deadcode   - Run vulture dead code checker"
	@echo "  make rebuild    - Build and run Docker containers (with prompts)"
	@echo "  make clean      - Stop and remove Docker containers"

check: lint format typecheck deadcode

lint:
	uv run ruff check --fix

format:
	uv run ruff format

typecheck:
	uv run ty check

deadcode:
	uv run vulture --min-confidence 100 --exclude ".venv" .

rebuild:
	@read -p "Rebuild without cache? (y/n): " nocache; \
	read -p "Remove volumes before rebuild? (y/n): " volumes; \
	if [ "$$volumes" = "y" ]; then \
		docker compose -f docker-compose.build.yml down -v; \
	else \
		docker compose -f docker-compose.build.yml down; \
	fi; \
	if [ "$$nocache" = "y" ]; then \
		PHOTON_VERSION=$(PHOTON_VERSION) docker compose -f docker-compose.build.yml build --no-cache; \
	else \
		PHOTON_VERSION=$(PHOTON_VERSION) docker compose -f docker-compose.build.yml build; \
	fi; \
	PHOTON_VERSION=$(PHOTON_VERSION) docker compose -f docker-compose.build.yml up

clean:
	docker compose -f docker-compose.build.yml down
