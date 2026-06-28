# ArtisanMarket

## Features Implemented

### 1. Product Search
inside `SearchService.search_products`:
- full-text search in PostgreSQL (GIN index on `name || description`)
- Redis cache of results (1-hour TTL)
- filtering by category and price range

### 2. Shopping Cart 
- session-based carts in Redis
- add / remove / update items (`add_item`, `remove_item`, `update_quantity`, `get_cart`)

### 3. Recommendation System
- "also bought" (`also_bought` → `get_also_bought` cypher query)
- "frequently bought together" (`frequently_bought_together` → `get_frequently_bought_together`)

### 4. Semantic Search
- embeddings generation (`VectorLoader.generate_and_store_embeddings`, all-MiniLM-L6-v2, 384-dim)
- vector similarity search (`SearchService.semantic_search` via pgvector cosine distance)

## How to Run

### Prerequisites
- Python 3.12+, `uv`, Docker

### 1. Start databases
```bash
docker-compose up -d
```

### 2. Configure environment
```bash
cp .env.example .env   # edit credentials if needed
```

### 3. Install dependencies
```bash
make setup
# or
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 4. Load data
```bash
# using make
make run-postgres-loader
make run-document-loader
make run-graph-loader
make run-vector-loader
make run-purchase-generator

# or all at once
make load-all

# or directly with uv
uv run python -m src.loaders.relational_loader
uv run python -m src.loaders.document_loader
uv run python -m src.loaders.graph_loader
uv run python -m src.loaders.vector_loader
uv run python -m src.utils.purchase_generator
```

### 5. Run the search service demo
```bash
make run-search-service
# or
uv run python -m src.services.search_service
```

### 6. Run tests
```bash
make test
# or
uv run pytest tests/ -v
```

## Project Structure

```
db-hw/
├── raw_data/                       
├── src/
│   ├── config.py                   
│   ├── db/
│   │   ├── postgres_client.py      
│   │   ├── mongodb_client.py       
│   │   ├── redis_client.py         
│   │   └── neo4j_client.py         
│   ├── loaders/
│   │   ├── relational_loader.py
│   │   ├── document_loader.py
│   │   ├── graph_loader.py
│   │   └── vector_loader.py
│   ├── services/
│   │   ├── search_service.py           
│   │   ├── cart_service.py            
│   │   └── recommendation_service.py
│   └── utils/
│       ├── data_parser.py
│       └── purchase_generator.py
├── tests/
│   └── test_artisan_market.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── README.md
└── uv.lock
```
