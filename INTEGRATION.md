# Integration: h3-api + g-etl

Detta dokument beskriver hur h3-api och g-etl hänger ihop.

## Översikt

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA PIPELINE                                │
│                                                                     │
│  ┌─────────────┐                      ┌─────────────────┐           │
│  │   g-etl     │                      │    h3-api       │           │
│  │  (ETL)      │                      │   (FastAPI)     │           │
│  │             │                      │                 │           │
│  │  Extract    │                      │  /hexbin        │           │
│  │     ↓       │   warehouse.duckdb   │  /heatmap       │           │
│  │  Transform  │ ──────────────────►  │  /cell/{id}    │           │
│  │     ↓       │    (läses av API)    │                 │           │
│  │  mart.*     │                      │  GeoJSON out    │           │
│  └─────────────┘                      └────────┬────────┘           │
│                                                │                     │
└────────────────────────────────────────────────┼─────────────────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │  Frontend Map   │
                                        │  (Kepler.gl,    │
                                        │   Mapbox, etc)  │
                                        └─────────────────┘
```

## Dataflöde

### 1. g-etl: ETL Pipeline

g-etl hämtar geodata från svenska myndigheter och indexerar med H3:

```
Skogsstyrelsen    ─┐
Naturvårdsverket  ─┼──► g-etl ──► warehouse.duckdb
SGU               ─┤            ├── mart.h3_cells
HAV               ─┘            ├── mart.naturreservat
                                └── mart.biotopskydd
```

**Relevanta tabeller för API:t:**

| Tabell | Innehåll |
|--------|----------|
| `mart.h3_cells` | Alla H3-celler med aggregerad data |
| `mart.{dataset}` | Dataset-specifika H3-celler |
| `mart.{dataset}_compact` | Kompakterade H3-celler |

### 2. h3-api: REST API

h3-api läser från warehouse.duckdb och exponerar data via REST:

```python
# h3-api läser direkt från g-etl:s databas
conn = duckdb.connect("../g-etl/data/warehouse.duckdb", read_only=True)
```

## Körning

### Separat (utveckling)

```bash
# Terminal 1: Kör g-etl pipeline
cd g-etl
task pipeline:run

# Terminal 2: Starta h3-api
cd h3-api
docker compose up
```

### Tillsammans (produktion)

```yaml
# docker-compose.yml (kombinerad)
services:
  etl:
    image: ghcr.io/10gbrand/g-etl:latest
    volumes:
      - data:/app/data

  api:
    build: ./h3-api
    volumes:
      - data:/app/data:ro  # Read-only access till samma data
    ports:
      - "8000:8000"
    depends_on:
      - etl

volumes:
  data:
```

## Schemaläggning

Typiskt körschema:

| Tid | Aktivitet |
|-----|-----------|
| 02:00 | g-etl: Kör nattlig pipeline |
| 02:30 | h3-api: Automatisk reload (om data ändrats) |
| Dagtid | h3-api: Serverar requests |

## Felsökning

### h3-api hittar inte databasen

```bash
# Verifiera att warehouse.duckdb finns
ls -la ../g-etl/data/warehouse.duckdb

# Kontrollera miljövariabel
echo $H3_API_DATABASE_PATH
```

### Tabeller saknas

```bash
# Kör g-etl pipeline först
cd ../g-etl
task pipeline:run

# Verifiera tabeller
duckdb data/warehouse.duckdb -c "SELECT table_name FROM information_schema.tables WHERE table_schema='mart'"
```

### API returnerar tom data

```bash
# Kontrollera att h3_cells finns och har data
duckdb ../g-etl/data/warehouse.duckdb -c "SELECT COUNT(*) FROM mart.h3_cells"
```

## Relaterade dokument

- [g-etl README](../g-etl/README.md)
- [g-etl INTEGRATION.md](../g-etl/INTEGRATION.md)
