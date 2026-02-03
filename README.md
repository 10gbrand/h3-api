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
# Starta devbox-miljö (installerar uv, task, etc.)
devbox shell

# Installera dependencies
task py:install-dev

# Starta utvecklingsserver
task dev

# API:t är tillgängligt på http://localhost:8000
```

#### Utan devbox

```bash
pip install uv
uv pip install -e ".[dev]"
uv run uvicorn h3_api.main:app --reload
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

### Devbox

Projektet använder [devbox](https://www.jetify.com/devbox) för att hantera utvecklingsverktyg:

```bash
# Starta devbox-miljö
devbox shell
```

Inkluderade verktyg: `uv`, `go-task`, `gh`, `claude-code`, `curl`, `jq`, `tree`

### Task-kommandon

Vanliga kommandon (kör `task --list` för alla):

| Kommando | Beskrivning |
|----------|-------------|
| `task dev` | Starta API med auto-reload |
| `task test` | Kör tester |
| `task fix` | Fixa lint/format automatiskt |
| `task py:ci` | CI-kontroller (format, lint, test) |
| `task py:precommit` | Fixa + verifiera innan commit |
| `task api:health` | Testa health endpoint |
| `task api:ready` | Testa ready endpoint |
| `task api:docs` | Öppna Swagger docs |

### Tester

```bash
task test
# eller
uv run pytest
```

### Linting

```bash
task fix
# eller
uv run ruff check . --fix
uv run ruff format .
```
