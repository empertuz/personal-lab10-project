import asyncio
import sqlite3

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import create_schema_sync
from app.services.geo import register_haversine_udf


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def sync_db(tmp_db_path):
    """A sync sqlite3 connection with schema and UDF for unit tests."""
    conn = sqlite3.connect(tmp_db_path)
    conn.row_factory = sqlite3.Row
    register_haversine_udf(conn)
    create_schema_sync(conn)
    yield conn
    conn.close()


def _seed_test_data(conn: sqlite3.Connection) -> None:
    """Insert a small set of test stations and rainfall data."""
    stations = [
        (
            "11010010",
            "LA VUELTA",
            "Pluviométrica",
            "Convencional",
            "Activa",
            98,
            5.458944,
            -76.544722,
            "Choco",
            "Cértegui",
            True,
        ),
        (
            "27015090",
            "AEROPUERTO OLAYA HERRERA",
            "Sinóptica Principal",
            "Automática",
            "Activa",
            1490,
            6.2206,
            -75.5906,
            "Antioquia",
            "Medellín",
            True,
        ),
        (
            "99999999",
            "STATION NO DATA",
            "Pluviométrica",
            "Convencional",
            "Suspendida",
            500,
            7.0,
            -74.0,
            "Santander",
            "Bucaramanga",
            False,
        ),
    ]
    conn.executemany(
        """INSERT INTO stations (id, name, category, technology, status,
           altitude, latitude, longitude, department, municipality, has_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        stations,
    )

    # Rainfall for station 11010010
    rainfall = [
        ("11010010", "2020-01-01", 5.0),
        ("11010010", "2020-01-02", 0.0),
        ("11010010", "2020-01-03", 12.5),
        ("11010010", "2020-06-15", 30.0),
        ("27015090", "2020-03-01", 8.0),
        ("27015090", "2020-03-02", 0.0),
    ]
    conn.executemany(
        "INSERT INTO rainfall_daily (station_id, date, value_mm) VALUES (?, ?, ?)",
        rainfall,
    )

    # Monthly aggregations
    monthly_sql = (
        "INSERT INTO rainfall_monthly"
        " (station_id, year, month, total_mm, avg_mm, max_mm,"
        " rainy_days, data_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn.execute(monthly_sql, ("11010010", 2020, 1, 17.5, 5.83, 12.5, 2, 3))
    conn.execute(monthly_sql, ("11010010", 2020, 6, 30.0, 30.0, 30.0, 1, 1))
    conn.execute(monthly_sql, ("27015090", 2020, 3, 8.0, 4.0, 8.0, 1, 2))

    # Yearly aggregations
    yearly_sql = (
        "INSERT INTO rainfall_yearly"
        " (station_id, year, total_mm, avg_daily_mm, max_daily_mm,"
        " rainy_days, data_days) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    conn.execute(yearly_sql, ("11010010", 2020, 47.5, 11.875, 30.0, 3, 4))
    conn.execute(yearly_sql, ("27015090", 2020, 8.0, 4.0, 8.0, 1, 2))

    conn.commit()


@pytest_asyncio.fixture
async def async_client(tmp_db_path):
    """AsyncClient backed by the FastAPI app with a seeded test DB."""
    import aiosqlite

    from app.main import app
    from app.services.geo import haversine, register_haversine_udf

    # Create and seed the sync DB first
    conn_sync = sqlite3.connect(tmp_db_path)
    conn_sync.row_factory = sqlite3.Row
    register_haversine_udf(conn_sync)
    create_schema_sync(conn_sync)
    _seed_test_data(conn_sync)
    conn_sync.close()

    # Open async connection for the app
    db = await aiosqlite.connect(tmp_db_path)
    db.row_factory = aiosqlite.Row
    # Register UDF via aiosqlite's thread-safe method
    await db.create_function("haversine", 4, haversine)

    app.state.db = db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await db.close()
