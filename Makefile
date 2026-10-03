.DEFAULT_GOAL := help
.PHONY: help install lint format test scan lint-docs hooks clean

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-22s %s\n", $$1, $$2}'

install: ## Create .venv from uv.lock (with dev tools)
	uv sync --locked

lint: ## Ruff lint + format check + mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

format: ## Auto-fix lint issues and format
	uv run ruff check --fix .
	uv run ruff format .

test: ## Run the test suite with coverage (fails under 90%)
	uv run pytest --cov --cov-report=term-missing

scan: ## Secret scan: gitleaks over full history + denylist scan
	gitleaks git --no-banner --redact --config .gitleaks.toml .
	scripts/denylist_scan.sh

lint-docs: ## Fail if any em dash (U+2014) appears in docs/ or *.md
	bash scripts/no_emdash.sh

hooks: ## Enable the repo's git hooks (required once per clone)
	git config core.hooksPath .githooks
	@echo "hooks enabled: .githooks/pre-push will run gitleaks + denylist scan"

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
