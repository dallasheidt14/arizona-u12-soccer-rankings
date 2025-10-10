.PHONY: setup lint test fmt ci

PY=python
PIP=pip

setup:
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov pandas pyarrow

test:
	pytest -q --disable-warnings --maxfail=1

cov:
	pytest -q --disable-warnings --maxfail=1 --cov=. --cov-report=term-missing

lint:
	@echo "Add ruff/black here if desired"

fmt:
	@echo "Add black -l 100 . if desired"

ci: setup test
