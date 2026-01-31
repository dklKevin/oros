.PHONY: help setup setup-dev test test-ingestion test-retrieval test-cov test-e2e test-e2e-up test-e2e-down lint format clean \
        docker-up docker-down docker-build db-migrate db-reset deploy-dev deploy-prod

# Default target
help:
	@echo "Biomedical Knowledge Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  setup          - Install production dependencies"
	@echo "  setup-dev      - Install development dependencies and pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  docker-up      - Start all services with Docker Compose"
	@echo "  docker-down    - Stop all services"
	@echo "  docker-build   - Build Docker images"
	@echo "  docker-logs    - View service logs"
	@echo ""
	@echo "Database:"
	@echo "  db-migrate     - Run database migrations"
	@echo "  db-reset       - Reset database (WARNING: destroys data)"
	@echo "  db-shell       - Open psql shell to database"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all unit tests"
	@echo "  test-ingestion - Run ingestion service tests"
	@echo "  test-retrieval - Run retrieval service tests"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  test-e2e       - Run E2E tests (requires Docker)"
	@echo "  test-e2e-up    - Start E2E test database"
	@echo "  test-e2e-down  - Stop E2E test database"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           - Run linters (ruff, mypy)"
	@echo "  format         - Format code (black, ruff --fix)"
	@echo "  typecheck      - Run mypy type checking"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-dev     - Deploy to dev environment"
	@echo "  deploy-prod    - Deploy to production environment"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          - Remove generated files and caches"

# =============================================================================
# Setup
# =============================================================================
setup:
	pip install -r requirements.txt

setup-dev:
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "Development environment ready!"

# =============================================================================
# Docker
# =============================================================================
docker-up:
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker-compose ps

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# =============================================================================
# Database
# =============================================================================
db-migrate:
	alembic upgrade head

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose exec postgres psql -U biomedical -d knowledge_platform -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	alembic upgrade head

db-shell:
	docker-compose exec postgres psql -U biomedical -d knowledge_platform

db-seed:
	python scripts/seed-data.py

# =============================================================================
# Testing
# =============================================================================
test:
	pytest services/ -v --tb=short

test-ingestion:
	pytest services/ingestion/tests -v --tb=short

test-retrieval:
	pytest services/retrieval/tests -v --tb=short

test-cov:
	pytest services/ -v --cov=services --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-watch:
	pytest-watch services/ -- -v --tb=short

# E2E Tests (require Docker)
test-e2e:
	@./scripts/run-e2e-tests.sh

test-e2e-verbose:
	@./scripts/run-e2e-tests.sh -v

test-e2e-up:
	docker-compose -f docker-compose.e2e.yml up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@docker-compose -f docker-compose.e2e.yml ps

test-e2e-down:
	docker-compose -f docker-compose.e2e.yml down -v --remove-orphans

test-all: test test-e2e
	@echo "All tests completed!"

# =============================================================================
# Code Quality
# =============================================================================
lint:
	ruff check services/
	mypy services/ --ignore-missing-imports

format:
	black services/ --line-length 100
	ruff check services/ --fix

typecheck:
	mypy services/ --ignore-missing-imports --show-error-codes

# =============================================================================
# Deployment
# =============================================================================
deploy-dev:
	cd infrastructure/terraform/environments/dev && terraform init && terraform apply

deploy-prod:
	@echo "WARNING: Deploying to production!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	cd infrastructure/terraform/environments/prod && terraform init && terraform apply

tf-plan-dev:
	cd infrastructure/terraform/environments/dev && terraform init && terraform plan

tf-plan-prod:
	cd infrastructure/terraform/environments/prod && terraform init && terraform plan

# =============================================================================
# Utilities
# =============================================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleaned up generated files"

# Run a specific service locally (for debugging)
run-ingestion:
	cd services/ingestion && uvicorn src.main:app --reload --port 8001

run-retrieval:
	cd services/retrieval && uvicorn src.main:app --reload --port 8000
