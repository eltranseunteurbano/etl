"""Configuración central del proyecto ETL.

Carga variables de entorno desde .env y expone rutas y parámetros
usados por todos los sub-pipelines.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

SOURCES_FOLDER: Path = ROOT / "data" / "sources"
VENTAS_FOLDER: Path = SOURCES_FOLDER / "ventas"
PELUQUERIA_FOLDER: Path = SOURCES_FOLDER / "peluqueria"

RAW_FOLDER: Path = ROOT / "data" / "raw"
INTERIM_FOLDER: Path = ROOT / "data" / "interim"
PROCESSED_FOLDER: Path = ROOT / "data" / "processed"
STATE_FILE: Path = ROOT / "data" / "state.json"

VENTAS_RAW_DIR: Path = RAW_FOLDER / "ventas"
VENTAS_INTERIM_DIR: Path = INTERIM_FOLDER / "ventas"
PELUQUERIA_RAW_DIR: Path = RAW_FOLDER / "peluqueria"
PELUQUERIA_INTERIM_DIR: Path = INTERIM_FOLDER / "peluqueria"
DATABASE_PATH: Path = ROOT / "data" / "warehouse.sqlite"
