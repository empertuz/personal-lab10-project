# Technical Brief: PluvioApp Backend and Project Structure

**Scope:** Build the backend (FastAPI + SQLite) and full project structure for the Pluviometric Station Analysis Platform. Historical data is available under `resources/data/` (station catalog + time-series files). Frontend and future analytical features are out of scope.

---

## 1. Task Title

**PluvioApp Phase 1 — Backend API and Project Structure (FastAPI + SQLite)**

---

## 2. Context

- **Current state:** A technical specification exists (`docs/pluvioapp-tech-spec-v1.1.md`) defining architecture, schema, API, and ingestion. The repository has no backend code yet; only the spec and historical data under `resources/data/` (IDEAM station catalog `CNE_IDEAM.csv` and 4,400+ pipe-delimited time-series files `PTPM_CON_INTER*.data`).
- **Pain points:** No runnable API, no database, no way to query stations by location or serve rainfall data. The spec assumes data under `data/source/`; in this project the single source of truth is `resources/data/` (catalog and `.data` files in the same directory).
- **Goal:** Deliver a working backend that (1) follows the spec’s project layout and tech stack, (2) ingests from `resources/data/` into SQLite, (3) exposes the Phase 1 API (station search by lat/lon/radius, station detail, rainfall daily/monthly/yearly and area-based monthly), and (4) is testable and ready for a future frontend.

---

## 3. Technical Requirements

- **Language and runtime:** Python 3.11+.
- **API:** FastAPI with async handlers; OpenAPI at `/docs`; CORS configurable via settings.
- **Database:** SQLite 3 via `aiosqlite`. Single file DB (path configurable; e.g. `data/pluvioapp.db`). No ORM: raw SQL with parameterized queries. Haversine registered as a SQLite UDF for exact distance filtering after a bounding-box pass.
- **Schema (English snake_case, content in Spanish where from source):**
  - **stations:** id (PK), name, category, technology, status, installed_at, suspended_at, altitude, latitude, longitude, department, municipality, operational_area, hydro_area, hydro_zone, hydro_subzone, stream, has_data. Indexes on latitude, longitude, status, category.
  - **rainfall_daily:** station_id (FK), date (YYYY-MM-DD), value_mm. PK (station_id, date). Indexes on station_id, date, (station_id, date).
  - **rainfall_monthly / rainfall_yearly:** Materialized aggregations (total_mm, avg_mm, max_mm, rainy_days, data_days) populated during ingestion (and optionally via a separate rebuild script).
- **Column mapping:** As in spec Section 5.5 (CODIGO→id, NOMBRE→name, etc.; Fecha→date, Valor→value_mm; station_id from filename). Handle stations that appear only in `.data` files (e.g. 10000000) by either inserting minimal station rows or skipping FK constraint for unknown stations—document the choice.
- **Data sources (this project):**
  - **Catalog:** `resources/data/CNE_IDEAM.csv` — ISO-8859-1, semicolon-delimited, CRLF. Columns as in spec.
  - **Time-series:** All `PTPM_CON_INTER*.data` under `resources/data/` (actual filenames use `@`, e.g. `PTPM_CON_INTER@11010010.data`). Pipe-delimited, header `Fecha|Valor`, ISO-8859-1; date as `YYYY-MM-DD HH:MM:SS` (strip to YYYY-MM-DD). Ingestion must glob and parse this naming pattern (e.g. `PTPM_CON_INTER@<id>.data` or `PTPM_CON_INTER_<id>.data`).
- **Config:** `pydantic-settings` + `.env`. At least: `DATABASE_PATH`, `DATA_DIR` (directory containing `.data` files), `CATALOG_PATH` (path to CNE_IDEAM.csv), `API_HOST`, `API_PORT`, `CORS_ORIGINS`, `LOG_LEVEL`. Defaults must point to `resources/data` for catalog and data directory so the app runs without moving files.
- **Project structure (from spec, adapted for data under `resources/data`):  
  `app/` (main.py, config.py, database.py; models/, routers/, services/, utils/); `scripts/` (ingest.py, build_aggregations.py); `data/` (for generated `pluvioapp.db` only; source data remains in `resources/data`); `docs/`; `tests/`; `pyproject.toml`, `.env.example`, `.gitignore`, `README.md`.
- **Ingestion (`scripts/ingest.py`):** Idempotent one-shot CLI: create/drop schema, load catalog from CATALOG_PATH, glob *.data from DATA_DIR, parse and bulk-insert rainfall_daily (batch/transaction per file, optional parallel workers), set stations.has_data from rainfall_daily, then build rainfall_monthly and rainfall_yearly. Target: full run < 90 s for ~4.4k files / ~5M rows with SQLite PRAGMAs (e.g. WAL, synchronous=OFF, cache_size).
- **Geo search:** Two-pass: (1) bounding-box filter using indexed lat/lon and degree deltas from radius_km; (2) Haversine UDF on the candidate set to filter by exact distance. Return stations with distance_km; optional filters: status, category, has_data.
- **API endpoints (Phase 1):**  
  Stations: GET `/api/stations/search` (lat, lon, radius_km, optional status, category, has_data), GET `/api/stations/{id}`, GET `/api/stations` (pagination, filters).  
  Rainfall: GET `/api/rainfall/{station_id}/daily` (date_from, date_to), GET `/api/rainfall/{station_id}/monthly` (year_from, year_to), GET `/api/rainfall/{station_id}/yearly`, POST `/api/rainfall/area/monthly` (body: lat, lon, radius_km, year_from, year_to), GET `/api/rainfall/{station_id}/stats`.  
  System: GET `/api/health`, POST `/api/admin/ingest` (protected).
- **Request/response contracts:** Align with spec Section 11 (e.g. StationSearchParams with Colombia lat/lon bounds, StationResponse with data_summary, RainfallDaily/RainfallMonthly Pydantic models).

---

## 4. Constraints

- **Forbidden:** ORMs (e.g. SQLAlchemy); PostgreSQL or other DB for Phase 1; changing source file encoding or column semantics (Spanish content preserved).
- **Required:** Type hints on all public functions and API models; parameterized SQL only (no string-interpolated queries); Pydantic v2 for settings and request/response models.
- **Code standards:** Follow existing or project-standard lint/format (e.g. ruff or flake8, black or ruff format); no bare `except:`; async endpoints use `async def` and async DB access.
- **Data path:** Do not assume data lives under `data/source/raw/`; use config (CATALOG_PATH, DATA_DIR) so that `resources/data` works as the default data root.
- **Filenames:** Ingestion must support the actual pattern `PTPM_CON_INTER@<id>.data` (and optionally `PTPM_CON_INTER_<id>.data`) so all files in `resources/data` are discoverable.
- **Edge cases:** Stations in `.data` but not in catalog (handle without failing ingestion); empty or malformed rows (skip or log and skip); date range validation on API (reject date_to < date_from); pagination required where listing all stations or large result sets.
- **Accessibility/performance:** API responses must be JSON; geo and list endpoints should respond in < 500 ms under typical load for the defined data size.

---

## 5. Definition of Done

- [ ] **Project layout:** Repository contains `app/` (main.py, config.py, database.py, models/, routers/, services/, utils/), `scripts/` (ingest.py, build_aggregations.py), `data/` (empty except generated DB), `docs/`, `tests/`, `pyproject.toml`, `.env.example`, `.gitignore`, `README.md` with run/ingest instructions.
- [ ] **Config:** App and ingest script read DATABASE_PATH, CATALOG_PATH, DATA_DIR from pydantic-settings; defaults point to `resources/data` for catalog and data dir; `.env.example` documents all variables.
- [ ] **Schema:** SQLite DB has tables `stations`, `rainfall_daily`, `rainfall_monthly`, `rainfall_yearly` with columns and indexes as in this brief; Haversine UDF registered when opening the DB.
- [ ] **Ingestion:** Running `scripts/ingest.py` with data in `resources/data` completes without error; `SELECT COUNT(*) FROM stations` returns &gt; 0; `SELECT COUNT(*) FROM rainfall_daily` returns &gt; 0; `rainfall_monthly` and `rainfall_yearly` populated; stations with at least one rainfall record have `has_data = TRUE`.
- [ ] **Ingestion performance:** Full ingest of all files in `resources/data` finishes in under 90 seconds on a modern laptop (or document hardware if not met).
- [ ] **Station search:** GET `/api/stations/search?lat=6.25&lon=-75.57&radius_km=50` returns JSON with `center`, `radius_km`, `count`, and `stations` array; each station includes `distance_km`; optional query params `status`, `category`, `has_data` filter results.
- [ ] **Station detail/list:** GET `/api/stations/{id}` returns 200 with station payload (or 404); GET `/api/stations` returns paginated list with optional filters.
- [ ] **Rainfall endpoints:** GET daily/monthly/yearly for a station_id return correct date ranges and values; POST `/api/rainfall/area/monthly` returns monthly data for stations in the given circle; GET `/api/rainfall/{station_id}/stats` returns summary stats (date range, counts, avg/max/min, coverage).
- [ ] **Health and admin:** GET `/api/health` returns DB status and record counts; POST `/api/admin/ingest` triggers re-ingestion (protection mechanism present even if minimal).
- [ ] **Tests:** `pytest` (with `pytest-asyncio`) runs successfully; at least: one test for geo/Haversine or bounding box, one for station search (or DB query), one for a rainfall endpoint or service; no skipped tests that are required for DoD.
- [ ] **Lint/format:** Project passes the chosen linter and formatter with zero errors (e.g. `ruff check .` and `ruff format --check .` or equivalent).
- [ ] **Docs:** README explains how to install deps, set `.env`, run ingestion, and start the API; `/docs` (Swagger) lists all Phase 1 endpoints.

---

## Quality Checklist (Verified)

- [x] All 5 sections present and non-vague
- [x] DoD fully verifiable (pass/fail criteria)
- [x] Constraints consistent with requirements (paths configurable; filename pattern clarified)
- [x] Brief consistent with existing spec and repo (data under `resources/data`; backend-only scope)
