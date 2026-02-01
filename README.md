# H3 API

FastAPI service for serving H3 hexbin/heatmap data from [g-etl](../g-etl).

## Snabbstart

### Med Docker (rekommenderat)

```bash
# Starta API:t (kopplas automatiskt till g-etl:s databas)
docker compose up

# API:t är tillgängligt på http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

### Lokal utveckling

```bash
# Installera dependencies
pip install uv
uv sync

# Starta utvecklingsserver
uv run uvicorn h3_api.main:app --reload

# Eller
uv run python -m h3_api.main
```

## Endpoints

| Endpoint | Beskrivning |
|----------|-------------|
| `GET /hexbin?bbox=...&res=9` | Hämta H3-celler inom bbox |
| `GET /hexbin/viewport?bbox=...&res=9` | Tom H3-grid för overlay |
| `GET /hexbin/cell/{cell_id}` | Detaljer för specifik cell |
| `GET /health` | Health check |
| `GET /ready` | Readiness med databasstatus |

### Exempel

```bash
# Hämta hexbins för södra Sverige
curl "http://localhost:8000/hexbin?bbox=11.0,55.0,14.0,58.0&res=7"

# Inspektera en specifik cell
curl "http://localhost:8000/hexbin/cell/871f24a81ffffff"
```

## Konfiguration

Miljövariabler (prefix `H3_API_`):

| Variabel | Default | Beskrivning |
|----------|---------|-------------|
| `H3_API_DATABASE_PATH` | `../g-etl/data/warehouse.duckdb` | Sökväg till DuckDB |
| `H3_API_DEFAULT_RESOLUTION` | `9` | Standard H3-resolution |
| `H3_API_MAX_CELLS_PER_REQUEST` | `10000` | Max celler per request |
| `H3_API_CORS_ORIGINS` | `["*"]` | Tillåtna CORS origins |

## Integration med g-etl

Se [INTEGRATION.md](INTEGRATION.md) för hur projekten hänger ihop.

## Arkitektur

```
Frontend (map)
     │
     ▼
┌─────────────────┐
│   H3 API        │
│   (FastAPI)     │
│     │           │
│     ▼           │
│   DuckDB        │◄──── warehouse.duckdb från g-etl
│   (read-only)   │
└─────────────────┘
```

## Utveckling

### Tester

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```
