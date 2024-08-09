MYPY_CACHE ?= .mypy_cache

.PHONY: lint
lint: mypy ruff

.PHONY: lint-fix
lint-fix: ruff-fix

.PHONY: test
test:
	pytest .

.PHONY: mypy
mypy:
	mypy --config-file pyproject.toml --cache-dir $(MYPY_CACHE) .

.PHONY: ruff
ruff:
	ruff format --check
	ruff check .

.PHONY: ruff-fix
ruff-fix:
	ruff format
	ruff check . --fix
