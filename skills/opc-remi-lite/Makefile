.PHONY: install test lint format clean build publish

install:
	pip install -e .
	pip install -r requirements-test.txt

test:
	pytest tests/ -v --cov=remi_lite --cov-report=term-missing

test-coverage:
	pytest tests/ -v --cov=remi_lite --cov-report=xml --cov-report=html

lint:
	flake8 remi_lite tests --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 remi_lite tests --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
	mypy remi_lite --ignore-missing-imports

format:
	black remi_lite tests
	isort remi_lite tests

format-check:
	black --check remi_lite tests
	isort --check remi_lite tests

security:
	bandit -r remi_lite -f json -o bandit-report.json || true
	bandit -r remi_lite || true

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	@echo "Publishing to ClawHub..."
	@echo "Run: clawhub publish . --slug opc-remi-lite --version 1.0.0"

ci: format-check lint test security
	@echo "All CI checks passed!"
