# PluvioApp

Pluviometric Station Analysis Platform — IDEAM data backend.

FastAPI + SQLite backend that ingests Colombian IDEAM weather station data (~4,777 stations, ~5M daily rainfall records) and exposes a REST API for geographic station search and rainfall queries.

## Setup

```bash
# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env if needed (defaults work with resources/data/)
```

## Data Ingestion

Source data must be in `resources/data/`:
- `CNE_IDEAM.csv` — station catalog
- `PTPM_CON_INTER@*.data` — rainfall time-series files

Run the ingestion script (creates/recreates the SQLite database):

```bash
python scripts/ingest.py
```

This drops and recreates all tables, loads the catalog, parses all `.data` files using 8 parallel reader threads, marks stations that have data, and builds monthly/yearly aggregation tables.

To rebuild aggregations without re-ingesting:

```bash
python scripts/build_aggregations.py
```

## Run the API

```bash
uvicorn app.main:app --reload
```

API docs available at [http://localhost:8000/docs](http://localhost:8000/docs).

## API Endpoints

### Stations
- `GET /api/stations/search?lat=6.25&lon=-75.57&radius_km=50` — find stations by location
- `GET /api/stations/{id}` — station detail
- `GET /api/stations/` — paginated station list

### Rainfall
- `GET /api/rainfall/{station_id}/daily?date_from=2020-01-01&date_to=2020-12-31`
- `GET /api/rainfall/{station_id}/monthly?year_from=2020&year_to=2024`
- `GET /api/rainfall/{station_id}/yearly`
- `GET /api/rainfall/{station_id}/stats`
- `POST /api/rainfall/area/monthly` — monthly data for all stations in an area

### System
- `GET /api/health` — DB status and record counts
- `POST /api/admin/ingest` — trigger re-ingestion (requires `X-Admin-Key` header)

## Tests

```bash
pytest -v
```

## Lint

```bash
ruff check .
ruff format --check .
```

## Configuration

All settings are configurable via `.env` or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./data/pluvioapp.db` | Path to SQLite database |
| `DATA_DIR` | `./resources/data` | Directory containing `.data` files |
| `CATALOG_PATH` | `./resources/data/CNE_IDEAM.csv` | Path to station catalog |
| `API_HOST` | `0.0.0.0` | API bind host |
| `API_PORT` | `8000` | API bind port |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins |
| `LOG_LEVEL` | `info` | Logging level |
| `ADMIN_KEY` | `changeme` | Key for admin endpoints |
