# OpenClaw OPC200 Project

## Development Commands

.PHONY: help install install-dev test test-unit test-integration test-e2e coverage lint format type-check security clean build docker-build docker-test

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# Testing
test: ## Run all tests
	pytest tests/ -v --timeout=120

test-unit: ## Run unit tests only
	pytest tests/unit -v --timeout=60

test-integration: ## Run integration tests only
	pytest tests/integration -v --timeout=120

test-e2e: ## Run end-to-end tests only
	pytest tests/e2e -v --timeout=300

test-fast: ## Run tests marked as fast
	pytest tests/ -v -m "not slow" --timeout=60

# Skills Testing
test-skills: ## Run all skills tests
	cd skills/opc-journal-suite && pytest tests/ -v --cov=. --cov-report=term

test-skills-coverage: ## Run skills tests with coverage report
	cd skills/opc-journal-suite && pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	@echo "Skills coverage report: skills/opc-journal-suite/htmlcov/index.html"

test-skills-watch: ## Run skills tests in watch mode (auto-rerun on change)
	cd skills/opc-journal-suite && ptw -- -v

test-skills-matrix: ## Run skills tests on all Python versions
	cd skills/opc-journal-suite && \
	for version in 3.10 3.11 3.12; do \
		echo "=== Testing with Python $$version ==="; \
		python$$version -m pytest tests/ -v || exit 1; \
	done

# TDD Commands
tdd-red: ## Run tests (expect failure - Red phase)
	@echo "🔴 Red phase: Running tests (expect failures)"
	cd skills/opc-journal-suite && pytest tests/ -v --tb=short || true

tdd-green: ## Run tests (expect success - Green phase)
	@echo "🟢 Green phase: Running tests (expect success)"
	cd skills/opc-journal-suite && pytest tests/ -v
tdd-refactor: tdd-green ## Run tests after refactoring
	@echo "🔵 Refactor phase complete: All tests passing"

tdd-coverage: ## Check coverage meets threshold
	cd skills/opc-journal-suite && pytest tests/ --cov=. --cov-fail-under=80 -v

coverage: ## Generate coverage report
	pytest tests/ --cov=src --cov-report=xml --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated: htmlcov/index.html"

coverage-view: coverage ## Generate and view coverage report
	open htmlcov/index.html

# Code Quality
lint: ## Run linters (flake8, pylint)
	flake8 src tests --max-line-length=127 --extend-ignore=E203,W503
	pylint src --max-line-length=127 --disable=R,C

format: ## Format code with black and isort
	black src tests
	isort src tests

format-check: ## Check code formatting
	black --check src tests
	isort --check-only src tests

type-check: ## Run type checking with mypy
	mypy src --ignore-missing-imports

security: ## Run security checks
	bandit -r src/
	safety check

pre-commit: format lint type-check security ## Run all pre-commit checks

# Building
build: ## Build Python package
	python -m build

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker
docker-build-test: ## Build test Docker image
	docker build -f Dockerfile.test -t opc200:test .

docker-build-prod: ## Build production Docker image
	docker build -f Dockerfile.prod -t opc200:prod .

docker-test: ## Run tests in Docker
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

docker-run-prod: ## Run production Docker compose
	docker-compose -f docker-compose.prod.yml up -d

docker-stop: ## Stop Docker containers
	docker-compose -f docker-compose.test.yml down
	docker-compose -f docker-compose.prod.yml down

# CI/CD Helpers
ci-test: ## Run CI test suite
	pytest tests/unit tests/integration -v --cov=src --cov-report=xml --timeout=120

ci-lint: ## Run CI lint checks
	flake8 src tests --max-line-length=127
	black --check src tests
	isort --check-only src tests
	mypy src --ignore-missing-imports

ci-security: ## Run CI security checks
	bandit -r src/
	detect-secrets scan --all-files

# Version Management
VERSION_FILE := VERSION

version: ## Show current version
	@cat $(VERSION_FILE)

bump-patch: ## Bump patch version
	@bash scripts/bump-version.sh patch

bump-minor: ## Bump minor version
	@bash scripts/bump-version.sh minor

bump-major: ## Bump major version
	@bash scripts/bump-version.sh major
