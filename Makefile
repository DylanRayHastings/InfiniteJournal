# Makefile for Infinite Journal

# Variables
PYTHON := python
PIP := pip
SRC_DIR := src
TEST_DIR := tests
DOC_DIR := docs
PACKAGE := infinitejournal

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Detect OS
ifeq ($(OS),Windows_NT)
    PYTHON := python
    RM := del /Q /F
    RMDIR := rmdir /S /Q
    SEP := \\
else
    PYTHON := python3
    RM := rm -f
    RMDIR := rm -rf
    SEP := /
endif

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Infinite Journal Development Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make [target]"
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  $(GREEN)%-20s$(NC) %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install the package in development mode
	@echo "$(BLUE)Installing Infinite Journal...$(NC)"
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)Installation complete!$(NC)"

.PHONY: install-prod
install-prod: ## Install the package in production mode
	@echo "$(BLUE)Installing Infinite Journal (production)...$(NC)"
	$(PIP) install .
	@echo "$(GREEN)Installation complete!$(NC)"

.PHONY: deps
deps: ## Install all dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements/base.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

.PHONY: deps-dev
deps-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements/develop.txt
	@echo "$(GREEN)Development dependencies installed!$(NC)"

.PHONY: deps-update
deps-update: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade -r requirements/base.txt
	$(PIP) install --upgrade -r requirements/develop.txt
	@echo "$(GREEN)Dependencies updated!$(NC)"

.PHONY: run
run: ## Run the application
	@echo "$(BLUE)Starting Infinite Journal...$(NC)"
	$(PYTHON) run.py

.PHONY: debug
debug: ## Run the application in debug mode
	@echo "$(BLUE)Starting Infinite Journal (debug mode)...$(NC)"
	INFINITEJOURNAL_DEBUG=true $(PYTHON) run.py

.PHONY: test
test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-fast
test-fast: ## Run tests in parallel
	@echo "$(BLUE)Running tests (parallel)...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR) -n auto -v

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(PACKAGE) --cov-report=html --cov-report=term-missing

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(PYTHON) -m pytest-watch $(TEST_DIR)

.PHONY: lint
lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	@make lint-black
	@make lint-isort  
	@make lint-flake8
	@make lint-mypy
	@echo "$(GREEN)All linting checks passed!$(NC)"

.PHONY: lint-black
lint-black: ## Run Black formatter check
	@echo "$(YELLOW)Running Black...$(NC)"
	$(PYTHON) -m black --check $(SRC_DIR)

.PHONY: lint-isort
lint-isort: ## Run isort import checker
	@echo "$(YELLOW)Running isort...$(NC)"
	$(PYTHON) -m isort --check-only $(SRC_DIR)

.PHONY: lint-flake8
lint-flake8: ## Run Flake8 linter
	@echo "$(YELLOW)Running Flake8...$(NC)"
	$(PYTHON) -m flake8 $(SRC_DIR)

.PHONY: lint-mypy
lint-mypy: ## Run MyPy type checker
	@echo "$(YELLOW)Running MyPy...$(NC)"
	$(PYTHON) -m mypy $(SRC_DIR)

.PHONY: format
format: ## Format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)Code formatted!$(NC)"

.PHONY: format-check
format-check: ## Check if code needs formatting
	@echo "$(BLUE)Checking code format...$(NC)"
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort --check-only $(SRC_DIR) $(TEST_DIR)

.PHONY: clean
clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	$(RMDIR) build dist *.egg-info .pytest_cache .coverage htmlcov .mypy_cache .tox
	find . -type d -name __pycache__ -exec $(RMDIR) {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type f -name ".coverage.*" -delete
	@echo "$(GREEN)Clean complete!$(NC)"

.PHONY: clean-logs
clean-logs: ## Clean log files
	@echo "$(BLUE)Cleaning log files...$(NC)"
	$(RMDIR) logs
	find . -type f -name "*.log" -delete
	@echo "$(GREEN)Logs cleaned!$(NC)"

.PHONY: build
build: clean ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)Build complete!$(NC)"

.PHONY: publish-test
publish-test: ## Publish to TestPyPI
	@echo "$(BLUE)Publishing to TestPyPI...$(NC)"
	$(PYTHON) -m twine upload --repository testpypi dist/*

.PHONY: publish
publish: ## Publish to PyPI
	@echo "$(RED)Publishing to PyPI...$(NC)"
	@echo "$(YELLOW)Are you sure? [y/N]$(NC)"
	@read ans && [ $${ans:-N} = y ]
	$(PYTHON) -m twine upload dist/*

.PHONY: docs
docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	cd $(DOC_DIR) && make html
	@echo "$(GREEN)Documentation built! Open docs/build/html/index.html$(NC)"

.PHONY: docs-serve
docs-serve: docs ## Build and serve documentation
	@echo "$(BLUE)Serving documentation...$(NC)"
	cd $(DOC_DIR)/build/html && $(PYTHON) -m http.server

.PHONY: docs-clean
docs-clean: ## Clean documentation build
	@echo "$(BLUE)Cleaning documentation...$(NC)"
	cd $(DOC_DIR) && make clean

.PHONY: profile
profile: ## Run the application with profiling
	@echo "$(BLUE)Running with profiler...$(NC)"
	$(PYTHON) -m cProfile -o profile.stats run.py
	@echo "$(GREEN)Profile saved to profile.stats$(NC)"

.PHONY: profile-view
profile-view: ## View profiling results
	@echo "$(BLUE)Viewing profile results...$(NC)"
	$(PYTHON) -m pstats profile.stats

.PHONY: benchmark
benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	$(PYTHON) -m pytest benchmarks/ -v

.PHONY: check-security
check-security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(PYTHON) -m bandit -r $(SRC_DIR)
	$(PYTHON) -m safety check
	@echo "$(GREEN)Security checks passed!$(NC)"

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"

.PHONY: diagnostic
diagnostic: ## Run system diagnostic
	@echo "$(BLUE)Running system diagnostic...$(NC)"
	$(PYTHON) diagnostic.py

.PHONY: version
version: ## Show version information
	@echo "$(BLUE)Infinite Journal Version Information$(NC)"
	@$(PYTHON) -c "import infinitejournal; print(f'Version: {infinitejournal.__version__}')"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Platform: $$($(PYTHON) -c 'import platform; print(platform.platform())')"

.PHONY: dev-setup
dev-setup: deps-dev pre-commit-install ## Complete development setup
	@echo "$(GREEN)Development environment setup complete!$(NC)"
	@echo "Run 'make help' to see available commands"

.PHONY: release
release: clean test lint build ## Prepare a release
	@echo "$(GREEN)Release preparation complete!$(NC)"
	@echo "1. Update version in pyproject.toml and __init__.py"
	@echo "2. Update CHANGELOG.md"
	@echo "3. Commit changes"
	@echo "4. Tag the release: git tag -a v0.x.x -m 'Release v0.x.x'"
	@echo "5. Push: git push origin main --tags"
	@echo "6. Run: make publish"

.PHONY: all
all: clean install test lint ## Run clean, install, test, and lint

# Default target
.DEFAULT_GOAL := help