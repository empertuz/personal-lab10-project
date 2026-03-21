import sqlite3

import aiosqlite

from app.config import get_settings
from app.services.geo import register_haversine_udf

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stations (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    category        TEXT,
    technology      TEXT,
    status          TEXT,
    installed_at    TEXT,
    suspended_at    TEXT,
    altitude        REAL,
    latitude        REAL,
    longitude       REAL,
    department      TEXT,
    municipality    TEXT,
    operational_area TEXT,
    hydro_area      TEXT,
    hydro_zone      TEXT,
    hydro_subzone   TEXT,
    stream          TEXT,
    has_data        BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_stations_lat ON stations(latitude);
CREATE INDEX IF NOT EXISTS idx_stations_lon ON stations(longitude);
CREATE INDEX IF NOT EXISTS idx_stations_status ON stations(status);
CREATE INDEX IF NOT EXISTS idx_stations_category ON stations(category);

CREATE TABLE IF NOT EXISTS rainfall_daily (
    station_id      TEXT NOT NULL,
    date            TEXT NOT NULL,
    value_mm        REAL NOT NULL,
    PRIMARY KEY (station_id, date),
    FOREIGN KEY (station_id) REFERENCES stations(id)
);

CREATE INDEX IF NOT EXISTS idx_rainfall_station ON rainfall_daily(station_id);
CREATE INDEX IF NOT EXISTS idx_rainfall_date ON rainfall_daily(date);
CREATE INDEX IF NOT EXISTS idx_rainfall_station_date ON rainfall_daily(station_id, date);

CREATE TABLE IF NOT EXISTS rainfall_monthly (
    station_id      TEXT NOT NULL,
    year            INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    total_mm        REAL,
    avg_mm          REAL,
    max_mm          REAL,
    rainy_days      INTEGER,
    data_days       INTEGER,
    PRIMARY KEY (station_id, year, month)
);

CREATE TABLE IF NOT EXISTS rainfall_yearly (
    station_id      TEXT NOT NULL,
    year            INTEGER NOT NULL,
    total_mm        REAL,
    avg_daily_mm    REAL,
    max_daily_mm    REAL,
    rainy_days      INTEGER,
    data_days       INTEGER,
    PRIMARY KEY (station_id, year)
);
"""

DROP_SQL = """
DROP TABLE IF EXISTS rainfall_yearly;
DROP TABLE IF EXISTS rainfall_monthly;
DROP TABLE IF EXISTS rainfall_daily;
DROP TABLE IF EXISTS stations;
"""

PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA cache_size=-64000",
    "PRAGMA foreign_keys=ON",
]


def create_schema_sync(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes on a synchronous connection."""
    conn.executescript(SCHEMA_SQL)


def drop_schema_sync(conn: sqlite3.Connection) -> None:
    """Drop all tables on a synchronous connection."""
    conn.executescript(DROP_SQL)


def apply_pragmas_sync(conn: sqlite3.Connection) -> None:
    """Apply performance pragmas on a synchronous connection."""
    for pragma in PRAGMAS:
        conn.execute(pragma)


def get_sync_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Open a synchronous sqlite3 connection with pragmas and UDF."""
    path = db_path or get_settings().DATABASE_PATH
    conn = sqlite3.connect(path)
    apply_pragmas_sync(conn)
    register_haversine_udf(conn)
    return conn


async def get_async_connection(db_path: str | None = None) -> aiosqlite.Connection:
    """Open an async aiosqlite connection with pragmas and UDF."""
    path = db_path or get_settings().DATABASE_PATH
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    for pragma in PRAGMAS:
        await conn.execute(pragma)
    # Register UDF via aiosqlite's thread-safe create_function
    from app.services.geo import haversine

    await conn.create_function("haversine", 4, haversine)
    return conn
