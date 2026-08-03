CORE_DIR ?= $(shell if [ -d ../core ]; then printf "../core"; else printf "core"; fi)
CORE_ROOT ?= $(shell dirname "$(CORE_DIR)")
PYTHONPATH := .:$(CORE_ROOT)
POETRY_RUN := PYTHONPATH=$(PYTHONPATH) poetry run
PROTO_SRC_DIR := $(CORE_DIR)/grpc_server/proto
PROTO_OUT_DIR := $(CORE_DIR)/grpc_server/generated
PROTO_FILES := $(shell find $(PROTO_SRC_DIR) -name '*.proto')

.PHONY: init-project start-grpc-server proto proto-gen fix-proto-imports test open-test-coverage

init-project:
	poetry install --with dev
	$(POETRY_RUN) pre-commit install
	$(POETRY_RUN) pre-commit install-hooks

start-grpc-server:
	$(POETRY_RUN) python -m core.grpc_server.server

proto: proto-gen

proto-gen:
	@mkdir -p $(PROTO_OUT_DIR)
	@touch $(PROTO_OUT_DIR)/__init__.py
	$(POETRY_RUN) python -m grpc_tools.protoc \
		-I $(PROTO_SRC_DIR) \
		--python_out=$(PROTO_OUT_DIR) \
		--pyi_out=$(PROTO_OUT_DIR) \
		--grpc_python_out=$(PROTO_OUT_DIR) \
		$(PROTO_FILES)
	@find $(PROTO_OUT_DIR) -type d -exec touch {}/__init__.py \;
	@$(MAKE) fix-proto-imports

fix-proto-imports:
	@$(POETRY_RUN) python scripts/fix_proto_imports.py $(PROTO_OUT_DIR) $(PROTO_SRC_DIR)

test:
	@mkdir -p tests/htmlcov
	COVERAGE_FILE=tests/.coverage $(POETRY_RUN) pytest

open-test-coverage:
	open tests/htmlcov/coverage/index.html
