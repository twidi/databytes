PROJECT_NAME := $(shell python setup.py --name)
PROJECT_VERSION := $(shell python setup.py --version)
SOURCE_ROOT := "src/$(PROJECT_NAME)"
TESTS_ROOT := "tests"

BOLD := \033[1m
RESET := \033[0m

default: help

.PHONY : help
help:  ## Show this help
	@echo "$(BOLD)$(PROJECT_NAME) project Makefile $(RESET)"
	@echo "Please use 'make $(BOLD)target$(RESET)' where $(BOLD)target$(RESET) is one of:"
	@grep -h ':\s\+##' Makefile | column -t -s# | awk -F ":" '{ print "  $(BOLD)" $$1 "$(RESET)" $$2 }'

.PHONY: install
install:  ## Install the project in the current environment, with its dependencies
	@echo "$(BOLD)Installing $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@pip install uv
	@uv pip install .

.PHONY: dev
dev:  ## Install the project in the current environment, with its dependencies, including the ones needed in a development environment
	@echo "$(BOLD)Installing (or upgrading) $(PROJECT_NAME) $(PROJECT_VERSION) in dev mode (with all dependencies)$(RESET)"
	@pip install --upgrade pip setuptools uv
	@uv pip install --upgrade -e .[extra,dev]
	@$(MAKE) full-clean

.PHONY: build
build:  ## Build the package
build: clean
	@echo "$(BOLD)Building package$(RESET)"
	@python -m build

.PHONY: upload
upload:  ## Upload the package to PyPI
	@echo "$(BOLD)Uploading package to PyPI$(RESET)"
	@python -m twine upload dist/*

.PHONY: clean
clean:  ## Clean python build related directories and files
	@echo "$(BOLD)Cleaning$(RESET)"
	@rm -rf build dist $(SOURCE_ROOT).egg-info

.PHONY: full-clean
full-clean:  ## Like "clean" but will clean some other generated directories or files
full-clean: clean
	@echo "$(BOLD)Full cleaning$(RESET)"
	find ./ -type d  \( -name '__pycache__' -or -name '.pytest_cache' -or -name '.mypy_cache' -or -name '.ruff_cache'  \) -print0 | xargs -tr0 rm -r

.PHONY: tests test
test / tests:  ## Run tests for the whole project.
test: tests  # we allow "test" and "tests"
tests:
	@echo "$(BOLD)Running tests$(RESET)"
	@## we ignore error 5 from pytest meaning there is no test to run
	@pytest || ( ERR=$$?; if [ $${ERR} -eq 5 ]; then (exit 0); else (exit $${ERR}); fi )

.PHONY: tests-nocov
test-nocov / tests-nocov:  ## Run tests for the whole project without coverage.
test-nocov: tests-nocov  # we allow "test-nocov" and "tests-nocov"
tests-nocov:
	@echo "$(BOLD)Running tests (without coverage)$(RESET)"
	@## we ignore error 5 from pytest meaning there is no test to run
	@pytest --no-cov || ( ERR=$$?; if [ $${ERR} -eq 5 ]; then (exit 0); else (exit $${ERR}); fi )

.PHONY: tests-fail-fast
test-fail-fast / test-fast / tests-fast / test-fail / tests-fail / tests-fail-fast:  ## Run tests for the whole project without coverage, stopping at the first failure.
test-fail-fast: tests-fail-fast
test-fast: tests-fail-fast
tests-fast: tests-fail-fast
test-fail: tests-fail-fast
tests-fail: tests-fail-fast
tests-fail-fast:
	@echo "$(BOLD)Running tests (without coverage, stopping at first failure)$(RESET)"
	@## we ignore error 5 from pytest meaning there is no test to run
	@pytest -x --no-cov || ( ERR=$$?; if [ $${ERR} -eq 5 ]; then (exit 0); else (exit $${ERR}); fi )

.PHONY: lint
lint:  ## Run all linters (ruff-check, mypy)
lint: ruff-check mypy

.PHONY: check checks
check / checks:  ## Run all checkers (lint, tests)
check: checks
checks: lint tests

.PHONY: mypy
mypy:  ## Run the mypy tool
	@echo "$(BOLD)Running mypy$(RESET)"
	@mypy $(SOURCE_ROOT) $(TESTS_ROOT)

.PHONY: ruff-check
ruff-check:  ## Run the ruff tool in check mode
	@echo "$(BOLD)Running ruff check$(RESET)"
	@ruff check $(SOURCE_ROOT) $(TESTS_ROOT)
	@ruff check --select I $(SOURCE_ROOT) $(TESTS_ROOT)
	@ruff format --check $(SOURCE_ROOT) $(TESTS_ROOT)

.PHONY: ruff-fix
ruff-fix:  ## Run the ruff tool in fix mode
	@echo "$(BOLD)Running ruff format$(RESET) in fix only mode"
	@ruff check --select I --fix $(SOURCE_ROOT) $(TESTS_ROOT)
	@ruff check --fix --exit-zero $(SOURCE_ROOT) $(TESTS_ROOT)
	@ruff format $(SOURCE_ROOT) $(TESTS_ROOT)

.PHONY: pretty format
pretty / format:  ## Run all code beautifiers (ruff-fix)
pretty: format
format: ruff-fix

