.PHONY: lint
lint: ty ruff

.PHONY: lint-fix
lint-fix: ruff-fix

.PHONY: test
test:
	pytest .

.PHONY: ty
ty:
	ty check .

.PHONY: ruff
ruff:
	ruff format --check
	ruff check .

.PHONY: ruff-fix
ruff-fix:
	ruff format
	ruff check . --fix
