"""
Idempotent one-shot ingestion: catalog + rainfall data + aggregations.

Architecture: single-writer + multi-reader queue.
  - 8 parser threads read and transform .data files concurrently.
  - 1 writer thread opens its own DB connection and drains the queue.
"""

import logging
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database import (
    apply_pragmas_sync,
    create_schema_sync,
    drop_schema_sync,
    get_sync_connection,
)
from app.services.geo import register_haversine_udf
from app.utils.parsing import parse_catalog, parse_data_file
from scripts.build_aggregations import build_monthly, build_yearly

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NUM_PARSER_THREADS = 8
BATCH_SIZE = 500
SENTINEL = None  # signals end of queue


def _writer_thread(
    db_path: str,
    q: queue.Queue,
    catalog_station_ids: set[str],
    stats: dict,
) -> None:
    """Open own DB connection, drain queue, insert rainfall rows."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    apply_pragmas_sync(conn)
    conn.execute("PRAGMA synchronous=OFF")
    register_haversine_udf(conn)

    orphan_ids_inserted: set[str] = set()

    while True:
        item = q.get()
        if item is SENTINEL:
            q.task_done()
            break

        station_id, rows = item
        if not rows:
            q.task_done()
            continue

        # Handle orphan station
        if station_id not in catalog_station_ids and station_id not in orphan_ids_inserted:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO stations (id, has_data) VALUES (?, TRUE)",
                    (station_id,),
                )
                orphan_ids_inserted.add(station_id)
            except Exception as e:
                logger.warning(
                    "Failed to insert orphan station %s: %s",
                    station_id,
                    e,
                )

        try:
            conn.executemany(
                "INSERT OR IGNORE INTO rainfall_daily "
                "(station_id, date, value_mm) VALUES (?, ?, ?)",
                [(station_id, date, val) for date, val in rows],
            )
            conn.commit()
            stats["rows"] += len(rows)
            stats["files"] += 1
            if stats["files"] % 500 == 0:
                logger.info(
                    "  progress: %d files, %d rows",
                    stats["files"],
                    stats["rows"],
                )
        except Exception as e:
            logger.warning(
                "Failed to insert data for station %s: %s",
                station_id,
                e,
            )
            conn.rollback()

        q.task_done()

    stats["orphan_stations"] = len(orphan_ids_inserted)
    conn.close()


def _parser_thread(files: list[Path], q: queue.Queue) -> None:
    """Parse files and put (station_id, rows) tuples on the queue."""
    for fp in files:
        station_id, rows = parse_data_file(fp)
        if station_id is not None:
            q.put((station_id, rows))


def main() -> None:
    settings = get_settings()
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path_str = str(db_path)

    t0 = time.perf_counter()

    # 1. Create schema with a main-thread connection
    logger.info("Creating database at %s", db_path)
    conn = get_sync_connection(db_path_str)
    drop_schema_sync(conn)
    create_schema_sync(conn)

    # 2. Ingest catalog
    logger.info("Ingesting station catalog from %s", settings.CATALOG_PATH)
    stations = parse_catalog(Path(settings.CATALOG_PATH))

    for i in range(0, len(stations), BATCH_SIZE):
        batch = stations[i : i + BATCH_SIZE]
        conn.executemany(
            """INSERT OR IGNORE INTO stations
               (id, name, category, technology, status,
                installed_at, suspended_at, altitude,
                latitude, longitude, department, municipality,
                operational_area, hydro_area, hydro_zone,
                hydro_subzone, stream)
               VALUES (:id, :name, :category, :technology,
                       :status, :installed_at, :suspended_at,
                       :altitude, :latitude, :longitude,
                       :department, :municipality,
                       :operational_area, :hydro_area,
                       :hydro_zone, :hydro_subzone, :stream)""",
            batch,
        )
    conn.commit()
    catalog_ids = {s["id"] for s in stations if s.get("id")}
    logger.info("Inserted %d catalog stations", len(catalog_ids))

    # Close main-thread connection before writer opens its own
    conn.close()

    # 3. Glob .data files
    data_dir = Path(settings.DATA_DIR)
    data_files = sorted(data_dir.glob("PTPM_CON_INTER*.data"))
    logger.info("Found %d data files in %s", len(data_files), data_dir)

    # 4. Single-writer + multi-reader queue
    q: queue.Queue = queue.Queue(maxsize=100)
    stats = {"rows": 0, "files": 0, "orphan_stations": 0}

    writer = threading.Thread(
        target=_writer_thread,
        args=(db_path_str, q, catalog_ids, stats),
        daemon=True,
    )
    writer.start()

    # Split files across parser threads
    chunks = [[] for _ in range(NUM_PARSER_THREADS)]
    for i, fp in enumerate(data_files):
        chunks[i % NUM_PARSER_THREADS].append(fp)

    parsers = []
    for chunk in chunks:
        t = threading.Thread(target=_parser_thread, args=(chunk, q), daemon=True)
        t.start()
        parsers.append(t)

    # Wait for all parsers to finish, then signal writer to stop
    for t in parsers:
        t.join()
    q.put(SENTINEL)
    writer.join()

    logger.info(
        "Ingested %d files, %d rainfall rows, %d orphan stations",
        stats["files"],
        stats["rows"],
        stats["orphan_stations"],
    )

    # 5. Post-processing with a fresh main-thread connection
    conn = get_sync_connection(db_path_str)

    # Mark has_data
    conn.execute(
        "UPDATE stations SET has_data = TRUE "
        "WHERE id IN (SELECT DISTINCT station_id FROM rainfall_daily)"
    )
    conn.commit()

    # 6. Build aggregations
    logger.info("Building aggregation tables...")
    monthly = build_monthly(conn)
    yearly = build_yearly(conn)
    logger.info("Built %d monthly rows, %d yearly rows", monthly, yearly)

    elapsed = time.perf_counter() - t0
    logger.info("Full ingestion completed in %.1fs", elapsed)

    # Summary
    for table in (
        "stations",
        "rainfall_daily",
        "rainfall_monthly",
        "rainfall_yearly",
    ):
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table}"  # noqa: S608
        ).fetchone()[0]
        logger.info("  %s: %d rows", table, count)

    conn.close()


if __name__ == "__main__":
    main()
