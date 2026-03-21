import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CATALOG_COLUMN_MAP = {
    "CODIGO": "id",
    "NOMBRE": "name",
    "CATEGORIA": "category",
    "TECNOLOGIA": "technology",
    "ESTADO": "status",
    "FECHA_INSTALACION": "installed_at",
    "FECHA_SUSPENSION": "suspended_at",
    "ALTITUD": "altitude",
    "LATITUD": "latitude",
    "LONGITUD": "longitude",
    "DEPARTAMENTO": "department",
    "MUNICIPIO": "municipality",
    "AREA_OPERATIVA": "operational_area",
    "AREA_HIDROGRAFICA": "hydro_area",
    "ZONA_HIDROGRAFICA": "hydro_zone",
    "SUBZONA_HIDROGRAFICA": "hydro_subzone",
    "CORRIENTE": "stream",
}

# Matches PTPM_CON_INTER@12345678.data or PTPM_CON_INTER_12345678.data
_STATION_ID_RE = re.compile(r"PTPM_CON_INTER[@_](\d+)\.data$")


def parse_catalog(path: Path) -> list[dict]:
    """Parse CNE_IDEAM.csv and return a list of station dicts."""
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        dtype=str,
        on_bad_lines="skip",
    )
    df.columns = df.columns.str.strip()
    # Keep only columns we need
    cols_to_keep = [c for c in CATALOG_COLUMN_MAP if c in df.columns]
    df = df[cols_to_keep].rename(columns=CATALOG_COLUMN_MAP)

    # Coerce numeric fields
    for col in ("latitude", "longitude", "altitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Strip whitespace from string fields
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Replace NaN with None for clean dict output
    records = df.where(df.notna(), None).to_dict(orient="records")
    logger.info("Parsed %d stations from catalog", len(records))
    return records


def extract_station_id(filepath: Path) -> str | None:
    """Extract the station ID from a PTPM_CON_INTER filename."""
    m = _STATION_ID_RE.search(filepath.name)
    return m.group(1) if m else None


def parse_data_file(filepath: Path) -> tuple[str | None, list[tuple[str, float]]]:
    """Parse a single .data file. Returns (station_id, [(date, value_mm), ...])."""
    station_id = extract_station_id(filepath)
    if station_id is None:
        logger.warning("Could not extract station ID from %s", filepath.name)
        return None, []

    rows: list[tuple[str, float]] = []
    try:
        df = pd.read_csv(
            filepath,
            sep="|",
            encoding="latin-1",
            dtype=str,
            on_bad_lines="skip",
        )
        df.columns = df.columns.str.strip()
        if "Fecha" not in df.columns or "Valor" not in df.columns:
            logger.warning("Missing Fecha/Valor columns in %s", filepath.name)
            return station_id, []

        for _, row in df.iterrows():
            try:
                date_str = str(row["Fecha"]).strip().split(" ")[0]  # YYYY-MM-DD
                value = float(row["Valor"])
                rows.append((date_str, value))
            except (ValueError, TypeError):
                continue
    except Exception as e:
        logger.warning("Error parsing %s: %s", filepath.name, e)

    return station_id, rows
