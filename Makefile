# Atlas OS Makefile
# Cross-platform build and test automation

.PHONY: install test lint typecheck verify demo clean help

# Default target
help:
	@echo "Atlas OS - Build Targets"
	@echo ""
	@echo "  install      - Install package in editable mode with dev dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-runtime - Run runtime tests only"
	@echo "  test-ai      - Run AI tests only"
	@echo "  lint         - Run ruff linting"
	@echo "  typecheck    - Run mypy type checking"
	@echo "  verify       - Run full verification (install, test, lint, typecheck)"
	@echo "  demo         - Run demo script"
	@echo "  cli-smoke    - Run CLI smoke tests"
	@echo "  clean        - Clean build artifacts"
	@echo "  help         - Show this help"

# Install package in editable mode with dev dependencies
install:
	pip install -e ".[dev]"

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Run runtime tests only
test-runtime:
	python -m pytest tests/test_runtime/ -v --tb=short

# Run AI tests only
test-ai:
	python -m pytest tests/test_ai/ -v --tb=short

# Run linting
lint:
	python -m ruff check src/ tests/

# Run type checking
typecheck:
	python -m mypy src/

# Full verification pipeline
verify: install test lint typecheck cli-smoke
	@echo ""
	@echo "✅ All verification steps passed!"

# Run demo script
demo:
	python scripts/demo_runtime.py

# CLI smoke tests
cli-smoke:
	@echo "Running CLI smoke tests..."
	atlas --help
	atlas version
	atlas runtime status
	atlas runtime health
	atlas runtime services
	atlas config show
	atlas config validate
	atlas models list
	atlas provider list
	atlas provider health llama_cpp
	atlas session new
	atlas chat --message "test"
	atlas network status
	atlas network scan
	atlas voice status
	atlas plugins list
	atlas plugins create test-plugin
	atlas logs -n 10
	atlas runtime
	atlas doctor
	atlas apikey list
	@echo "✅ CLI smoke tests passed!"

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run with coverage
coverage:
	python -m pytest tests/ --cov=src/atlas --cov-report=term-missing --cov-report=html

# Format code
format:
	python -m ruff format src/ tests/
	python -m ruff check --fix src/ tests/