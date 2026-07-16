# ---------------------------------------
# Global
# ---------------------------------------
PYTHON         := .venv/bin/python
POETRY_RUN     := poetry run
#---------------------------------
# Init
# --------------------------------
.PHONY: init-project

init-project:
	poetry install --with dev
	$(POETRY_RUN) pre-commit install
	$(POETRY_RUN) pre-commit install-hooks


#---------------------------------
# Server
# --------------------------------
.PHONY: start server dev

start:
	$(POETRY_RUN) python -m app

server: start

dev:
	RELOAD=True $(POETRY_RUN) python -m app

# ---------------------------------------
# Scope: Celery
# ---------------------------------------
CELERY_APP ?= app.celery.celery:app
CELERY_QUEUE ?= my-app-queue-tasks
CELERY_FLOWER_PORT ?= 5555

.PHONY: celery-worker celery-worker-solo celery-beat celery-flower celery-purge

celery-worker:
	$(POETRY_RUN) celery -A $(CELERY_APP) worker\
		-l INFO \
		--autoscale=5,1 \
		--prefetch-multiplier=1 \
		-Ofair \
		-Q $(CELERY_QUEUE) \
		-n my_app_worker@%h \
		--max-tasks-per-child=1000

celery-beat:
	$(POETRY_RUN) celery -A $(CELERY_APP) beat -l INFO

celery-flower:
	$(POETRY_RUN) celery -A $(CELERY_APP) flower --port=$(CELERY_FLOWER_PORT)

celery-purge:
	$(POETRY_RUN) celery -A $(CELERY_APP) purge -Q $(CELERY_QUEUE) -f

# ---------------------------------------
# Scope: Migration
# ---------------------------------------
.PHONY: migrate-create migrate-create-empty migrate-up migrate-down migrate-history migrate-current

migrate-create:
	@if [ -z "$(MSG)" ]; then \
		$(POETRY_RUN) alembic revision --autogenerate -m "auto_gen_$$(date +'%Y%m%d_%H%M%S')"; \
	else \
		$(POETRY_RUN) alembic revision --autogenerate -m "$(MSG)"; \
	fi

migrate-up:
	$(POETRY_RUN) alembic upgrade head

migrate-down:
	$(POETRY_RUN) alembic downgrade -1

migrate-history:
	$(POETRY_RUN) alembic history


#---------------------------------
# Unit Tests
# --------------------------------
.PHONY: test open-test-coverage

test:
	@mkdir -p tests/htmlcov
	COVERAGE_FILE=tests/.coverage $(POETRY_RUN) pytest

open-test-coverage:
	open tests/htmlcov/coverage/index.html


# CLEAN UP
.PHONY: clean-up-pycache

clean-up-pycache:
	find . \
  \( -name "__pycache__" \
  -o -name ".ruff_cache" \
  -o -name ".pytest_cache" \
  -o -name ".mypy_cache" \
  -o -name ".coverage" \) \
  -exec rm -rf {} +
