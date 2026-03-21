"""Rebuild rainfall_monthly and rainfall_yearly from rainfall_daily."""

import sqlite3
import sys
import time
from pathlib import Path

# Allow running as: python scripts/build_aggregations.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import get_sync_connection

BUILD_MONTHLY_SQL = """
INSERT OR REPLACE INTO rainfall_monthly
    (station_id, year, month, total_mm, avg_mm, max_mm, rainy_days, data_days)
SELECT
    station_id,
    CAST(strftime('%Y', date) AS INTEGER) AS year,
    CAST(strftime('%m', date) AS INTEGER) AS month,
    SUM(value_mm),
    AVG(value_mm),
    MAX(value_mm),
    COUNT(CASE WHEN value_mm > 0 THEN 1 END),
    COUNT(*)
FROM rainfall_daily
GROUP BY station_id, year, month
"""

BUILD_YEARLY_SQL = """
INSERT OR REPLACE INTO rainfall_yearly
    (station_id, year, total_mm, avg_daily_mm, max_daily_mm, rainy_days, data_days)
SELECT
    station_id,
    CAST(strftime('%Y', date) AS INTEGER) AS year,
    SUM(value_mm),
    AVG(value_mm),
    MAX(value_mm),
    COUNT(CASE WHEN value_mm > 0 THEN 1 END),
    COUNT(*)
FROM rainfall_daily
GROUP BY station_id, year
"""


def build_monthly(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM rainfall_monthly")
    cursor = conn.execute(BUILD_MONTHLY_SQL)
    conn.commit()
    return cursor.rowcount


def build_yearly(conn: sqlite3.Connection) -> int:
    conn.execute("DELETE FROM rainfall_yearly")
    cursor = conn.execute(BUILD_YEARLY_SQL)
    conn.commit()
    return cursor.rowcount


def main() -> None:
    settings = get_settings()
    conn = get_sync_connection(settings.DATABASE_PATH)

    t0 = time.perf_counter()
    monthly = build_monthly(conn)
    yearly = build_yearly(conn)
    elapsed = time.perf_counter() - t0

    print(f"Built {monthly} monthly rows, {yearly} yearly rows in {elapsed:.1f}s")
    conn.close()


if __name__ == "__main__":
    main()
