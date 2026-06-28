setup:
	uv venv
	uv pip install -e .
	uv pip install -e ".[dev]"

run-postgres-loader:
	uv run python -m src.loaders.relational_loader

run-document-loader:
	uv run python -m src.loaders.document_loader

run-graph-loader:
	uv run python -m src.loaders.graph_loader

run-vector-loader:
	uv run python -m src.loaders.vector_loader

run-purchase-generator:
	uv run python -m src.utils.purchase_generator

run-search-service:
	uv run python -m src.services.search_service

load-all: run-postgres-loader run-document-loader run-graph-loader \
          run-vector-loader run-purchase-generator

test:
	uv run pytest tests/ -v

format:
	uv run ruff format .

lint:
	uv run ruff check .

.PHONY: setup run-postgres-loader run-document-loader run-graph-loader \
        run-vector-loader run-purchase-generator run-search-service \
        load-all test format lint
