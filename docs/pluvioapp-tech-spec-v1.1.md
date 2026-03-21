# PluvioApp — Technical Specification

**Pluviometric Station Analysis Platform**

Version 1.1 — March 2026 | Author: Tech Lead

*Data Source: IDEAM — Instituto de Hidrología, Meteorología y Estudios Ambientales*

---

## 1. Executive Summary

PluvioApp is a web application that allows users to define a geographic area of interest (via lat/lon coordinate + radius in km) and retrieve pluviometric (rainfall) data from IDEAM weather stations within that area. The system ingests ~4,777 station records from a master catalog (CNE_IDEAM.csv) and 500+ individual time-series data files (PTPM_CON_INTER_*.data) containing daily rainfall measurements spanning from the 1940s to 2025.

This document defines the backend architecture for Phase 1: a performant data-ingestion and query layer that can serve as the foundation for future analytical features.

---

## 2. Data Profile

### 2.1 Station Catalog (CNE_IDEAM.csv)

| Property | Value |
|----------|-------|
| Encoding | ISO-8859-1 (Latin-1), semicolon-delimited, CRLF line endings |
| Total Records | 4,777 stations |
| Columns | 20 fields: CODIGO, NOMBRE, CATEGORIA, TECNOLOGIA, ESTADO, FECHA_INSTALACION, FECHA_SUSPENSION, ALTITUD, LATITUD, LONGITUD, DEPARTAMENTO, MUNICIPIO, AREA_OPERATIVA, ENTIDAD, AREA_HIDROGRAFICA, ZONA_HIDROGRAFICA, SUBZONA_HIDROGRAFICA, CORRIENTE, OBSERVACION, SUBRED |
| Key Fields for App | CODIGO (station ID, PK), LATITUD, LONGITUD, NOMBRE, CATEGORIA, ESTADO, ALTITUD, DEPARTAMENTO, MUNICIPIO |
| Coordinate System | WGS84 decimal degrees (LATITUD positive = N, LONGITUD negative = W) |
| Station Categories | Pluviométrica (1,745), Limnimétrica (971), Limnigráfica (485), Climatológica Ordinaria (484), Climatológica Principal (408), Pluviográfica (173), others |

### 2.2 Time-Series Data Files (PTPM_CON_INTER_*.data)

| Property | Value |
|----------|-------|
| File Count | 500+ files (one per station with pluviometric data) |
| Format | Pipe-delimited (`\|`), header: `Fecha\|Valor`, ISO-8859-1 encoding |
| Fecha Column | Datetime string: `YYYY-MM-DD HH:MM:SS` (all timestamps at 07:00:00) |
| Valor Column | Float, daily rainfall in mm (e.g., 0.0, 30.0, 105.6) |
| Date Range | Varies per station: earliest 1943, latest 2025. Rows: 928 to 18,474 per file |
| Naming Convention | `PTPM_CON_INTER_{CODIGO}.data` — CODIGO maps to station catalog PK |
| Estimated Total Rows | ~5 million rows across all files |
| Known Quirks | Some station IDs (e.g. 10000000) exist in data files but NOT in the catalog. Date gaps are common (non-contiguous daily records) |

---

## 3. Architecture Decision: SQLite + Python

Given the data profile (~5M rows, read-heavy analytical workload, single-user or small-team usage, file-based source data), SQLite is the optimal choice for Phase 1. Here's the rationale:

| Criteria | SQLite | PostgreSQL / Other |
|----------|--------|--------------------|
| Setup | Zero config, single file, no server process | Requires server, credentials, migrations infra |
| Performance | 5M rows in-process = sub-100ms geo queries with spatial index | Faster for concurrent multi-user, overkill here |
| Portability | Single .db file, easy to version / share / backup | Requires pg_dump or Docker volume |
| Geo Support | SpatiaLite extension OR Haversine UDF (both excellent) | PostGIS (powerful but heavyweight) |
| Migration Path | Easy to migrate to Postgres later if needed | N/A |

**Recommendation: SQLite with a Python (FastAPI) backend.**

If the project scales to multi-user concurrent writes or needs real-time streaming, migrate to PostgreSQL + PostGIS. The data access layer will be abstracted to make this swap straightforward.

---

## 4. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Runtime | Python 3.11+ | Best-in-class data ecosystem (pandas, numpy) |
| API Framework | FastAPI | Async, auto-docs (Swagger), type-safe with Pydantic |
| Database | SQLite 3 (via aiosqlite) | Zero-config, single file, 5M rows with ease |
| Geo Queries | Haversine UDF + R-tree index | Lightweight, no native extensions needed |
| Data Ingestion | pandas + sqlite3 bulk insert | Fast CSV/data parsing, 500+ files in <60s |
| ORM / Query | Raw SQL via aiosqlite (no ORM) | Full control over geo + analytical queries |
| Config | pydantic-settings + .env | Type-safe config, env-driven |
| Testing | pytest + pytest-asyncio | Async test support for FastAPI |
| Package Manager | uv (or pip + venv) | Fast, modern Python package management |

---

## 5. Database Schema

All column names use English snake_case. Content values remain in the original Spanish (e.g. `status = 'Activa'`). The ingestion script maps source CSV columns to DB columns as shown in Section 5.5.

### 5.1 Table: stations

```sql
CREATE TABLE stations (
    id              TEXT PRIMARY KEY,    -- source: CODIGO, e.g. '11010010'
    name            TEXT NOT NULL,       -- source: NOMBRE
    category        TEXT,                -- source: CATEGORIA ('Pluviométrica', etc.)
    technology      TEXT,                -- source: TECNOLOGIA
    status          TEXT,                -- source: ESTADO ('Activa', 'Suspendida', etc.)
    installed_at    TEXT,                -- source: FECHA_INSTALACION
    suspended_at    TEXT,                -- source: FECHA_SUSPENSION
    altitude        REAL,                -- source: ALTITUD (meters)
    latitude        REAL NOT NULL,       -- source: LATITUD
    longitude       REAL NOT NULL,       -- source: LONGITUD
    department      TEXT,                -- source: DEPARTAMENTO
    municipality    TEXT,                -- source: MUNICIPIO
    operational_area TEXT,               -- source: AREA_OPERATIVA
    hydro_area      TEXT,                -- source: AREA_HIDROGRAFICA
    hydro_zone      TEXT,                -- source: ZONA_HIDROGRAFICA
    hydro_subzone   TEXT,                -- source: SUBZONA_HIDROGRAFICA
    stream          TEXT,                -- source: CORRIENTE
    has_data        BOOLEAN DEFAULT FALSE  -- TRUE if a .data file exists
);

-- Spatial bounding-box index for fast radius filtering
CREATE INDEX idx_stations_lat ON stations(latitude);
CREATE INDEX idx_stations_lon ON stations(longitude);
CREATE INDEX idx_stations_status ON stations(status);
CREATE INDEX idx_stations_category ON stations(category);
```

### 5.2 Table: rainfall_daily

```sql
CREATE TABLE rainfall_daily (
    station_id      TEXT NOT NULL,        -- FK to stations.id
    date            TEXT NOT NULL,         -- 'YYYY-MM-DD' (strip time from source)
    value_mm        REAL NOT NULL,         -- daily rainfall in mm
    PRIMARY KEY (station_id, date),
    FOREIGN KEY (station_id) REFERENCES stations(id)
);

-- Critical indexes for analytical queries
CREATE INDEX idx_rainfall_station ON rainfall_daily(station_id);
CREATE INDEX idx_rainfall_date ON rainfall_daily(date);
CREATE INDEX idx_rainfall_station_date ON rainfall_daily(station_id, date);
```

### 5.3 Table: rainfall_monthly (Materialized Aggregation)

Pre-computed monthly aggregations to avoid scanning millions of rows for common analytical queries. Populated during ingestion and refreshed on demand.

```sql
CREATE TABLE rainfall_monthly (
    station_id      TEXT NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    total_mm        REAL,                -- SUM of daily values
    avg_mm          REAL,                -- AVG daily rainfall
    max_mm          REAL,                -- MAX single-day rainfall
    rainy_days      INTEGER,             -- COUNT where value_mm > 0
    data_days       INTEGER,             -- COUNT of records (for coverage %)
    PRIMARY KEY (station_id, year, month)
);
```

### 5.4 Table: rainfall_yearly (Materialized Aggregation)

```sql
CREATE TABLE rainfall_yearly (
    station_id      TEXT NOT NULL,
    year            INTEGER NOT NULL,
    total_mm        REAL,
    avg_daily_mm    REAL,
    max_daily_mm    REAL,
    rainy_days      INTEGER,
    data_days       INTEGER,
    PRIMARY KEY (station_id, year)
);
```

### 5.5 Column Mapping: Source → Database

The ingestion script uses this mapping to translate CSV headers to DB columns. Content values (Spanish text) are preserved as-is.

**Station Catalog Mapping:**

| Source (CSV) | DB Column | Notes |
|-------------|-----------|-------|
| CODIGO | id | Primary key, TEXT |
| NOMBRE | name | Station name in Spanish |
| CATEGORIA | category | Values remain in Spanish |
| TECNOLOGIA | technology | |
| ESTADO | status | Activa / Suspendida / En Mantenimiento |
| FECHA_INSTALACION | installed_at | Keep as TEXT, source format DD/MM/YYYY |
| FECHA_SUSPENSION | suspended_at | Nullable |
| ALTITUD | altitude | Meters above sea level |
| LATITUD | latitude | WGS84 decimal degrees |
| LONGITUD | longitude | Negative = West |
| DEPARTAMENTO | department | |
| MUNICIPIO | municipality | |
| AREA_OPERATIVA | operational_area | |
| AREA_HIDROGRAFICA | hydro_area | |
| ZONA_HIDROGRAFICA | hydro_zone | |
| SUBZONA_HIDROGRAFICA | hydro_subzone | |
| CORRIENTE | stream | River/stream name |
| (computed) | has_data | Set TRUE if .data file exists |

**Rainfall Data Mapping:**

| Source (.data) | DB Column | Notes |
|---------------|-----------|-------|
| (from filename) | station_id | Extracted: `PTPM_CON_INTER_{ID}.data` |
| Fecha | date | Strip time, keep YYYY-MM-DD |
| Valor | value_mm | Daily rainfall in millimeters |

---

## 6. Geospatial Query Strategy

The radius search uses a two-pass approach for efficiency:

**Pass 1 — Bounding Box Filter (uses index, fast)**

Convert the radius (km) to approximate degree offsets and filter using indexed lat/lon columns. At Colombian latitudes (~2°–12°N), 1° latitude ≈ 111 km and 1° longitude ≈ 108–111 km.

```python
delta_lat = radius_km / 111.0
delta_lon = radius_km / (111.0 * cos(radians(center_lat)))

SELECT * FROM stations
WHERE latitude  BETWEEN :lat - :dlat AND :lat + :dlat
  AND longitude BETWEEN :lon - :dlon AND :lon + :dlon
```

**Pass 2 — Haversine Exact Distance (on the reduced set)**

Apply the Haversine formula as a registered SQLite UDF to compute exact great-circle distances and filter to the precise radius. This runs on ~10–100 candidates instead of 4,777.

```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))
```

Register this as a SQLite function so it can be used in WHERE and SELECT clauses.

---

## 7. Project Structure

```
pluvioapp/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan, CORS
│   ├── config.py                # Settings via pydantic-settings
│   ├── database.py              # SQLite connection, UDF registration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── station.py           # Pydantic schemas for stations
│   │   └── rainfall.py          # Pydantic schemas for rainfall data
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── stations.py          # /api/stations endpoints
│   │   └── rainfall.py          # /api/rainfall endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── geo.py               # Haversine, bounding box logic
│   │   ├── station_service.py   # Station lookup business logic
│   │   └── rainfall_service.py  # Rainfall query + aggregation logic
│   └── utils/
│       └── parsing.py           # CSV / .data file parsers
├── scripts/
│   ├── ingest.py                # One-shot ingestion: CSV + all .data files
│   └── build_aggregations.py    # Rebuild monthly/yearly tables
├── data/
│   ├── source/
│   │   ├── CNE_IDEAM.csv        # Station catalog (original, Latin-1)
│   │   └── raw/                 # All PTPM_CON_INTER_*.data files (500+)
│   │       ├── PTPM_CON_INTER_11010010.data
│   │       ├── PTPM_CON_INTER_11010020.data
│   │       └── ...              # ~500 more files
│   └── pluvioapp.db             # Generated SQLite database (gitignored)
├── docs/
│   ├── tech-spec.docx           # This document
│   ├── data-dictionary.md       # Column mapping: source CSV → DB schema
│   ├── api-examples.md          # cURL / httpie examples for all endpoints
│   └── architecture.md          # High-level architecture notes & ADRs
├── tests/
│   ├── test_geo.py
│   ├── test_stations.py
│   └── test_rainfall.py
├── pyproject.toml
├── .env.example
├── .gitignore                   # data/pluvioapp.db, .env, __pycache__
└── README.md
```

---

## 8. API Endpoints (Phase 1)

### 8.1 Station Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stations/search` | Core endpoint: find stations by lat, lon, radius_km. Returns list with distances. Filters: status, category, has_data |
| GET | `/api/stations/{id}` | Get single station detail with metadata + data availability summary |
| GET | `/api/stations` | List all stations with pagination. Filters: department, status, category |

### 8.2 Rainfall Data Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rainfall/{station_id}/daily` | Daily rainfall for one station. Params: date_from, date_to |
| GET | `/api/rainfall/{station_id}/monthly` | Monthly aggregations for one station. Params: year_from, year_to |
| GET | `/api/rainfall/{station_id}/yearly` | Yearly aggregations for one station |
| POST | `/api/rainfall/area/monthly` | Monthly rainfall for all stations in an area. Body: {lat, lon, radius_km, year_from, year_to} |
| GET | `/api/rainfall/{station_id}/stats` | Summary stats: date range, total records, avg/max/min rainfall, coverage % |

### 8.3 System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check: DB status, record counts, last ingestion date |
| POST | `/api/admin/ingest` | Trigger re-ingestion of all source files (protected) |

---

## 9. Data Ingestion Pipeline

The ingestion script (`scripts/ingest.py`) runs as a one-shot CLI command. It is idempotent: running it again drops and recreates all tables.

**Step 1: Create schema**
Execute all CREATE TABLE and CREATE INDEX statements.

**Step 2: Ingest station catalog**
Read CNE_IDEAM.csv with pandas (`encoding=latin-1, sep=';'`). Clean column names, parse lat/lon as floats. Insert all rows into the stations table via `executemany` with batch size of 500.

**Step 3: Ingest rainfall data files**
Glob all `PTPM_CON_INTER_*.data` files from the `data/source/raw/` directory. For each file: extract the station ID from the filename, parse with pandas (`sep='|', encoding='latin-1'`), extract date as YYYY-MM-DD string (strip the time component since it's always 07:00:00), and bulk-insert into rainfall_daily. Use transactions per file for atomicity. Process in parallel using a thread pool (4–8 workers) for I/O-bound speedup.

**Step 4: Mark stations with data**
After all .data files are ingested, `UPDATE stations SET has_data = TRUE WHERE id IN (SELECT DISTINCT station_id FROM rainfall_daily)`.

**Step 5: Build aggregation tables**
Run `INSERT INTO rainfall_monthly SELECT ... GROUP BY station_id, year, month` from rainfall_daily. Same for rainfall_yearly. This takes a single pass over the data.

**Performance Target:**
Full ingestion of 500+ files (~5M rows) should complete in under 90 seconds on a modern laptop. SQLite's bulk insert with WAL mode and PRAGMA optimizations (`synchronous=OFF, journal_mode=WAL, cache_size=-64000`) can handle 100K+ inserts/second.

---

## 10. Cursor Development Guide

When building this project in Cursor, use the following phased approach. Each phase produces a working, testable deliverable.

**Phase 1: Project Scaffolding + DB (Day 1)**
- Initialize project with pyproject.toml, install FastAPI, uvicorn, aiosqlite, pandas, pydantic-settings
- Create the full project structure from Section 7
- Implement database.py with SQLite connection pool, UDF registration, and schema creation
- Write and run the ingestion script with the sample files provided
- Verify: `sqlite3 pluvioapp.db 'SELECT COUNT(*) FROM stations; SELECT COUNT(*) FROM rainfall_daily;'`

**Phase 2: Core API — Station Search (Day 1–2)**
- Implement the Haversine UDF and bounding-box query in services/geo.py
- Build GET /api/stations/search with lat, lon, radius_km query params
- Add filtering by status, category, has_data
- Return results sorted by distance, include distance_km in response
- Write tests with known station coordinates

**Phase 3: Rainfall Endpoints (Day 2–3)**
- Implement daily, monthly, yearly rainfall endpoints per station
- Implement the area-based monthly aggregation endpoint
- Add date range validation and pagination

**Phase 4: Polish + Performance (Day 3)**
- Add CORS middleware for frontend consumption
- Add response caching for geo queries (lru_cache or Redis if needed later)
- Add health check endpoint with DB stats
- Verify all endpoints via Swagger UI at /docs

---

## 11. Request / Response Contracts

### 11.1 Station Search Request

```
GET /api/stations/search?lat=6.25&lon=-75.57&radius_km=50&has_data=true
```

### 11.2 Station Search Response

```json
{
  "center": { "lat": 6.25, "lon": -75.57 },
  "radius_km": 50,
  "count": 12,
  "stations": [
    {
      "id": "27015090",
      "name": "AEROPUERTO OLAYA HERRERA",
      "category": "Sinóptica Principal",
      "status": "Activa",
      "latitude": 6.2206,
      "longitude": -75.5906,
      "altitude": 1490,
      "department": "Antioquia",
      "municipality": "Medellín",
      "distance_km": 3.8,
      "has_data": true,
      "data_summary": {
        "date_from": "1952-01-01",
        "date_to": "2025-10-15",
        "total_records": 16350
      }
    }
  ]
}
```

### 11.3 Daily Rainfall Response

```json
{
  "station_id": "27015090",
  "date_from": "2024-01-01",
  "date_to": "2024-12-31",
  "count": 312,
  "data": [
    { "date": "2024-01-01", "value_mm": 0.0 },
    { "date": "2024-01-02", "value_mm": 12.4 }
  ]
}
```

---

## 12. Key Pydantic Models

```python
class StationSearchParams(BaseModel):
    lat: float = Field(..., ge=-4.0, le=13.5)    # Colombia bounds
    lon: float = Field(..., ge=-82.0, le=-66.0)
    radius_km: float = Field(..., gt=0, le=500)
    status: Optional[str] = None
    category: Optional[str] = None
    has_data: Optional[bool] = None

class StationResponse(BaseModel):
    id: str
    name: str
    category: Optional[str]
    status: Optional[str]
    latitude: float
    longitude: float
    altitude: Optional[float]
    department: Optional[str]
    municipality: Optional[str]
    distance_km: float
    has_data: bool
    data_summary: Optional[DataSummary]

class RainfallDaily(BaseModel):
    date: str
    value_mm: float

class RainfallMonthly(BaseModel):
    year: int
    month: int
    total_mm: float
    avg_mm: float
    max_mm: float
    rainy_days: int
    data_days: int
```

---

## 13. Configuration (.env)

```env
# .env.example
DATABASE_PATH=./data/pluvioapp.db
DATA_DIR=./data/source/raw
CATALOG_PATH=./data/source/CNE_IDEAM.csv
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
LOG_LEVEL=info
```

---

## 14. Future Phases (Out of Scope for Phase 1)

| Phase | Feature | Notes |
|-------|---------|-------|
| 2 | Interactive Map Frontend (React + Leaflet/Mapbox) | Click-to-search, station markers, radius overlay |
| 2 | Rainfall Charts (Recharts / Chart.js) | Time series, monthly bars, heatmaps |
| 3 | Multi-station Comparison | Overlay rainfall patterns from N stations |
| 3 | Anomaly Detection | Identify unusual rainfall events vs historical norms |
| 3 | Data Export (CSV, Excel, PDF reports) | Download filtered data and generated reports |
| 4 | IDF Curve Generation | Intensity-Duration-Frequency curves from station data |
| 4 | Spatial Interpolation (Kriging/IDW) | Estimate rainfall at ungauged points from nearby stations |
| 5 | Real-time IDEAM Integration | API connection to IDEAM live feeds if available |

---

## 15. Dependencies (pyproject.toml)

```toml
[project]
name = "pluvioapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "aiosqlite>=0.20.0",
    "pandas>=2.2.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
]
```
