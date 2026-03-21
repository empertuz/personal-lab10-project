# Implementation Plan: PluvioApp Phase 1 — Backend API and Project Structure

**Based on:** `docs/technical-brief-pluvioapp-backend-and-project-structure.md`
**Status:** Approved — ready for implementation

---

## 1. Summary

We are building the complete FastAPI + SQLite backend for PluvioApp from scratch. The app ingests ~4,445 IDEAM pluviometric time-series files and a 4,777-station catalog (both in `resources/data/`) into a SQLite database, then exposes a Phase 1 REST API for geographic station search and rainfall data queries. No ORM, no PostgreSQL, no frontend — pure async Python backend with a clean, testable structure ready for a future React frontend.

---

## 2. Step-by-Step Implementation Logic

**Step 1 — Project scaffolding**
What: Create the directory skeleton (`app/`, `app/models/`, `app/routers/`, `app/services/`, `app/utils/`, `scripts/`, `data/`, `tests/`) and the root config files: `pyproject.toml` (with all dependencies), `.env.example`, `.gitignore` (excluding `data/pluvioapp.db`, `.env`, `__pycache__`, `.ruff_cache`), and a stub `README.md`. No Python logic yet.
Why first: Every subsequent file lives inside this skeleton. Establishing it first avoids structural drift.
Depends on: nothing

**Step 2 — Configuration module**
What: Implement `app/config.py` using `pydantic-settings`. Define a `Settings` class with: `DATABASE_PATH`, `DATA_DIR`, `CATALOG_PATH`, `API_HOST`, `API_PORT`, `CORS_ORIGINS`, `LOG_LEVEL`, `ADMIN_KEY`. Default values for `DATA_DIR` and `CATALOG_PATH` point to `resources/data/` so the app works without an `.env` file. Export a singleton `get_settings()` with `@lru_cache`.
Why second: All other modules import settings. Centralising config avoids hardcoded paths everywhere.
Depends on: Step 1

**Step 3 — Database module**
What: Implement `app/database.py`. This module owns the SQLite connection lifecycle: it opens an `aiosqlite` connection, registers the Haversine function as a SQLite UDF (using Python's `math` module — no extensions), applies performance PRAGMAs (`journal_mode=WAL`, `synchronous=NORMAL`, `cache_size=-64000`, `foreign_keys=ON`), and runs the `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` statements for all four tables (`stations`, `rainfall_daily`, `rainfall_monthly`, `rainfall_yearly`). Exposes a `get_db()` async context manager for use in FastAPI dependencies. Also exposes a synchronous `create_schema_sync(conn)` helper for use in the ingestion script.
Why third: The schema must exist before any ingestion or service code references it.
Depends on: Step 2

**Step 4 — Pydantic models**
What: Implement `app/models/station.py` and `app/models/rainfall.py`. These are pure data contracts with no DB logic. Station models: `StationSearchParams` (with Colombia lat/lon bounds validation), `DataSummary`, `StationResponse`, `StationDetail`, `StationListParams`. Rainfall models: `RainfallDaily`, `RainfallMonthly`, `RainfallYearly`, `RainfallStats`, `AreaMonthlyRequest`, `AreaMonthlyResponse`. All use Pydantic v2 with `Field` validators.
Why here: Services and routers depend on these types. Defining them before services prevents circular imports.
Depends on: Step 1

**Step 5 — Parsing utilities**
What: Implement `app/utils/parsing.py`. Two functions: `parse_catalog(path)` reads `CNE_IDEAM.csv` with `pandas` (`encoding=latin-1`, `sep=';'`, `dtype=str` to preserve leading zeros in CODIGO), applies the column mapping from the brief (CODIGO→id, LATITUD→latitude, etc.), coerces lat/lon/altitude to float, and yields dicts. `parse_data_file(path)` reads one `PTPM_CON_INTER@{id}.data` file (`sep='|'`, `encoding=latin-1`), extracts station_id from the filename using a regex that handles both `@` and `_` separators, strips the time component from `Fecha` to `YYYY-MM-DD`, and yields `(station_id, date, value_mm)` tuples. Both functions skip and log malformed rows rather than raising.
Why before ingestion: The ingestion script calls these directly.
Depends on: Step 2

**Step 6 — Ingestion script**
What: Implement `scripts/ingest.py` as an idempotent CLI. Execution order: (1) drop all four tables if they exist, (2) create schema via `database.py`'s sync helper, (3) parse and bulk-insert all catalog rows into `stations` in batches of 500 using `executemany`, (4) glob all `PTPM_CON_INTER*.data` files from `DATA_DIR`, (5) process files using a single-writer + multi-reader queue pattern: 8 parser threads read and transform files concurrently and push results onto a queue; one dedicated writer thread drains the queue and inserts into `rainfall_daily` in per-file transactions. This avoids SQLite write-lock contention that would occur with 8 concurrent writers. (6) After the queue is drained, run `UPDATE stations SET has_data = TRUE WHERE id IN (SELECT DISTINCT station_id FROM rainfall_daily)`. (7) Call `build_aggregations.py` logic to populate `rainfall_monthly` and `rainfall_yearly`.

**Orphan station handling (documented decision):** Station IDs that appear in `.data` files but not in `CNE_IDEAM.csv` (e.g. `10000000`) are inserted as minimal rows in `stations` with `id` filled in and all metadata fields set to `NULL`, and `has_data=TRUE`. Rationale: preserves all rainfall data, keeps the API consistent (rainfall endpoints work for these stations), and allows metadata to be backfilled later if IDEAM publishes it. These stations won't appear in geo search results since their lat/lon is NULL — which is correct behaviour given their location is unknown.

Why this order: Catalog must be loaded before FK constraints matter. Single-writer queue is the main performance lever for the 90-second target.
Depends on: Steps 2, 3, 5

**Step 7 — Build aggregations script**
What: Implement `scripts/build_aggregations.py`. Two functions callable independently: `build_monthly(conn)` runs a single `INSERT OR REPLACE INTO rainfall_monthly SELECT ... GROUP BY station_id, year, month` from `rainfall_daily`. `build_yearly(conn)` does the same grouping by year only. Both delete existing rows before inserting. Can be run standalone via `python scripts/build_aggregations.py` or imported by the ingestion script.
Why separate: Allows re-aggregation without full re-ingestion.
Depends on: Steps 3, 6

**Step 8 — Geo service**
What: Implement `app/services/geo.py`. Three functions: `bounding_box(lat, lon, radius_km)` returns `(lat_min, lat_max, lon_min, lon_max)` using the degree-offset formula from the spec. `haversine(lat1, lon1, lat2, lon2)` returns the great-circle distance in km. `register_haversine_udf(conn)` registers `haversine` as a SQLite UDF on a connection object so it can be called from SQL. These are pure functions with no DB access.
Why separate module: Geo logic is testable in isolation and reused by both station and rainfall services.
Depends on: Step 1

**Step 9 — Station service**
What: Implement `app/services/station_service.py`. Three async functions: `search_stations(db, params)` — runs the two-pass geo query (bounding box via indexed lat/lon, then `WHERE haversine(...) <= radius_km`), applies optional `status`/`category`/`has_data` filters, returns a list of `StationResponse` sorted by distance. `data_summary` is only included when the caller passes `include_summary=True` (opt-in). `get_station(db, station_id)` — fetches one station by PK, raises 404 if not found. `list_stations(db, params)` — paginated listing (default `page_size=100`, max `500`) with optional `department`/`status`/`category` filters.
Depends on: Steps 3, 4, 8

**Step 10 — Rainfall service**
What: Implement `app/services/rainfall_service.py`. Five async functions: `get_daily(db, station_id, date_from, date_to)` — validates date range (raises 422 if date_to < date_from), queries `rainfall_daily`. `get_monthly(db, station_id, year_from, year_to)` — queries `rainfall_monthly`. `get_yearly(db, station_id)` — queries `rainfall_yearly`. `get_area_monthly(db, request)` — geo search then joins with `rainfall_monthly`. `get_stats(db, station_id)` — queries `rainfall_daily` for min/max date, count, avg/max/min, coverage percentage. All raise `HTTPException(404)` if station_id has no data.
Depends on: Steps 3, 4, 8

**Step 11 — Routers**
What: Implement `app/routers/stations.py` and `app/routers/rainfall.py`. Each is a `fastapi.APIRouter`. Station router prefix `/api/stations`: `GET /search`, `GET /`, `GET /{id}`. Rainfall router prefix `/api/rainfall`: `GET /{station_id}/daily`, `GET /{station_id}/monthly`, `GET /{station_id}/yearly`, `POST /area/monthly`, `GET /{station_id}/stats`. All handlers delegate to services and return typed Pydantic response models.
Depends on: Steps 4, 9, 10

**Step 12 — Main application**
What: Implement `app/main.py`. Creates the `FastAPI` app with title and version. Lifespan: on startup open the DB connection, register Haversine UDF, store in `app.state.db`; on shutdown close it. Add `CORSMiddleware` from settings. Include both routers. Add `GET /api/health` (DB status, record counts) and `POST /api/admin/ingest` (protected by `X-Admin-Key` header checked against `ADMIN_KEY` env var — returns 403 if missing or wrong).
Depends on: Steps 2, 3, 11

**Step 13 — Tests**
What: Implement `tests/test_geo.py`, `tests/test_stations.py`, `tests/test_rainfall.py` using pytest + pytest-asyncio + httpx. All tests use a temp-file SQLite DB seeded with fixture data — no dependency on the full dataset.
Depends on: Steps 8, 9, 10, 12

**Step 14 — README and .env.example**
What: Write the final `README.md` (install, configure, ingest, run) and populate `.env.example` with all variables.
Depends on: All prior steps

---

## 3. Files to Create

| File | Purpose | Key contents |
|------|---------|--------------|
| `pyproject.toml` | Project metadata and dependencies | fastapi, uvicorn, aiosqlite, pandas, pydantic-settings, python-dotenv; dev: pytest, pytest-asyncio, httpx, ruff |
| `.env.example` | Documents all env vars | DATABASE_PATH, DATA_DIR, CATALOG_PATH, API_HOST, API_PORT, CORS_ORIGINS, LOG_LEVEL, ADMIN_KEY |
| `.gitignore` | Excludes generated/sensitive files | data/pluvioapp.db, .env, __pycache__, .ruff_cache |
| `README.md` | Developer guide | Install, configure, ingest, run, test instructions |
| `app/__init__.py` | Package marker | Empty |
| `app/main.py` | FastAPI app entrypoint | App instance, lifespan, CORS, health + admin endpoints, router includes |
| `app/config.py` | Settings | Settings class, get_settings() |
| `app/database.py` | DB connection and schema | get_db(), create_schema_sync(), register_haversine_udf() |
| `app/models/__init__.py` | Package marker | Empty |
| `app/models/station.py` | Station Pydantic models | StationSearchParams, DataSummary, StationResponse, StationDetail, StationListParams |
| `app/models/rainfall.py` | Rainfall Pydantic models | RainfallDaily, RainfallMonthly, RainfallYearly, RainfallStats, AreaMonthlyRequest, AreaMonthlyResponse |
| `app/routers/__init__.py` | Package marker | Empty |
| `app/routers/stations.py` | Station API router | GET /search, GET /, GET /{id} |
| `app/routers/rainfall.py` | Rainfall API router | GET daily/monthly/yearly/stats, POST area/monthly |
| `app/services/__init__.py` | Package marker | Empty |
| `app/services/geo.py` | Geo helpers | haversine(), bounding_box(), register_haversine_udf() |
| `app/services/station_service.py` | Station business logic | search_stations(), get_station(), list_stations() |
| `app/services/rainfall_service.py` | Rainfall business logic | get_daily(), get_monthly(), get_yearly(), get_area_monthly(), get_stats() |
| `app/utils/__init__.py` | Package marker | Empty |
| `app/utils/parsing.py` | File parsers | parse_catalog(), parse_data_file() |
| `scripts/ingest.py` | Ingestion CLI | Idempotent one-shot: schema + catalog + rainfall + aggregations |
| `scripts/build_aggregations.py` | Aggregation rebuild | build_monthly(), build_yearly() |
| `data/.gitkeep` | Keeps data/ in git | Empty |
| `tests/__init__.py` | Package marker | Empty |
| `tests/test_geo.py` | Geo unit tests | haversine accuracy, bounding box |
| `tests/test_stations.py` | Station integration tests | Search, detail, list, filters, pagination |
| `tests/test_rainfall.py` | Rainfall integration tests | daily/monthly/yearly/stats/area endpoints |

---

## 4. Files to Modify

This is a greenfield project — no existing files to modify.

---

## 5. Risks and Unknowns

**Risk 1 — Orphan station IDs**
What: Station IDs in `.data` files not present in `CNE_IDEAM.csv`.
Why it matters: FK enforcement would fail ingestion; skipping loses data.
Resolution: **Insert minimal station rows with NULL metadata (chosen).** See Step 6 for full rationale.

**Risk 2 — Ingestion performance with 4,445 files**
What: SQLite WAL allows one writer at a time; 8 concurrent writers cause lock contention.
Why it matters: Could push ingestion beyond the 90-second target.
Resolution: **Single-writer + multi-reader queue pattern (chosen).** 8 parser threads feed one writer thread.

**Risk 3 — Filename pattern variability**
What: Files use `@` separator; brief also mentions `_`. Glob must not double-count.
Why it matters: A greedy regex could match both forms of the same station ID.
Resolution: Glob `PTPM_CON_INTER*.data` and extract ID with a regex accepting `@` or `_` as separator. Verify no duplicate files exist in `resources/data/` during testing.

**Risk 4 — Date parsing edge cases**
What: Spec says all timestamps are `YYYY-MM-DD 07:00:00` but real data may vary.
Why it matters: Strict parsing silently drops rows; loose parsing may insert bad data.
Resolution: Strip everything after the first space in `Fecha`, log invalid dates, skip the row. Never abort the whole file.

**Risk 5 — aiosqlite vs sqlite3 in the ingestion script**
What: Ingestion is a batch script, not an async handler. Mixing sync/async adds overhead and confusion.
Why it matters: Subtle bugs and worse performance.
Resolution: Use synchronous `sqlite3` directly in `scripts/ingest.py`. `database.py` exposes both an async version (for the app) and a `create_schema_sync()` helper (for the script).

---

## 6. Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Orphan station IDs | Insert minimal rows with NULL metadata | Preserves all rainfall data; consistent API behaviour; backfillable later |
| Admin endpoint protection | `X-Admin-Key` header vs `ADMIN_KEY` env var | Minimal but present; easy to upgrade later |
| Ingestion architecture | Single-writer + multi-reader queue | Avoids SQLite write-lock contention; typically faster than N concurrent writers |
| Pagination defaults | page_size=100, max 500 | Reasonable defaults for ~4,777 stations |
| data_summary on search | Opt-in via `?include_summary=true` | Avoids subquery overhead on every geo search; caller requests it explicitly |

---

## 7. Rollback and Safety Notes

This is a new project. There is nothing to roll back.

**Prerequisites before starting:**
- Python 3.11+ installed
- `uv` or `pip` + `venv` available
- `resources/data/` present and intact (confirmed: 4,445 `.data` files + `CNE_IDEAM.csv`)

**The generated `data/pluvioapp.db` is gitignored** — it is a derived artifact fully reproducible by running `scripts/ingest.py`. No migration infrastructure is needed for Phase 1; the ingestion script is idempotent.

---

## 8. Test Plan Preview

**test_geo.py — unit tests**
- `test_haversine_known_distance`: Two known points ~3.8 km apart, assert result within 0.5 km tolerance → DoD: geo/Haversine test
- `test_bounding_box_contains_point`: Point inside radius is within bounding box
- `test_bounding_box_excludes_point`: Point outside radius is outside bounding box

**test_stations.py — integration tests (temp SQLite DB with fixture data)**
- `test_search_returns_results`: Search near known coordinates returns results with `distance_km`
- `test_search_has_data_filter`: `has_data=true` filters out stations with no rainfall records
- `test_search_out_of_bounds_lat`: Latitude outside Colombia bounds returns 422
- `test_station_detail_found`: Known station ID returns 200 with correct fields
- `test_station_detail_not_found`: Unknown station ID returns 404
- `test_station_list_pagination`: `page_size=5` returns exactly 5 results with total count → DoD: station search test

**test_rainfall.py — integration tests**
- `test_daily_returns_data`: Daily records returned within requested date range
- `test_daily_invalid_range`: date_to < date_from returns 422
- `test_monthly_aggregation`: Monthly totals match known sums from fixture data
- `test_stats_endpoint`: Stats returns date_from, date_to, counts, avg/max/min
- `test_area_monthly`: POST area/monthly with valid body returns non-empty response
- `test_rainfall_unknown_station`: Unknown station_id returns 404 → DoD: rainfall endpoint test

---

## 9. Expected Results

**Externally observable behaviour when complete:**
- `python scripts/ingest.py` completes in < 90s, prints summary (stations loaded, rows loaded, aggregations built)
- `uvicorn app.main:app --reload` starts on `0.0.0.0:8000`
- `GET /docs` lists all 11 Phase 1 endpoints in Swagger UI
- `GET /api/stations/search?lat=6.25&lon=-75.57&radius_km=50&has_data=true` returns spec-compliant JSON
- `pytest` passes with zero failures
- `ruff check . && ruff format --check .` passes with zero errors

**DoD checklist:**

| DoD Item | Covered by |
|----------|-----------|
| Project layout complete | Step 1 |
| Config reads from env, defaults to resources/data | Step 2 |
| SQLite schema: all tables + indexes | Step 3 |
| Haversine UDF registered | Steps 3, 8 |
| Ingestion completes without error | Step 6 |
| stations COUNT > 0 after ingest | Step 6 |
| rainfall_daily COUNT > 0 after ingest | Step 6 |
| rainfall_monthly / yearly populated | Steps 6, 7 |
| has_data = TRUE for stations with records | Step 6 |
| Ingestion < 90 seconds | Step 6 (single-writer queue) |
| GET /api/stations/search returns correct JSON | Steps 9, 11 |
| GET /api/stations/{id} returns 200 or 404 | Steps 9, 11 |
| GET /api/stations paginated list | Steps 9, 11 |
| All rainfall endpoints return correct data | Steps 10, 11 |
| GET /api/health returns DB status | Step 12 |
| POST /api/admin/ingest is protected | Step 12 |
| pytest passes | Step 13 |
| ruff lint + format passes | pyproject.toml + all steps |
| README complete | Step 14 |
