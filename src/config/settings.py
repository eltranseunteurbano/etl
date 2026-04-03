"""Configuración central del proyecto ETL.

Carga variables de entorno desde .env y expone rutas y parámetros
usados por todos los sub-pipelines.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

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

# ── Alegra ───────────────────────────────────────────────────────────────────
ALEGRA_EMAIL: str = os.getenv("ALEGRA_EMAIL", "")
ALEGRA_TOKEN: str = os.getenv("ALEGRA_TOKEN", "")
ALEGRA_BASE_URL: str = os.getenv(
    "ALEGRA_BASE_URL", "https://api.alegra.com/api/v1"
)
ALEGRA_RAW_DIR: Path = RAW_FOLDER / "alegra"
ALEGRA_INTERIM_DIR: Path = INTERIM_FOLDER / "alegra"

# ── Google Calendar ──────────────────────────────────────────────────────────
GOOGLE_CLIENT_SECRETS_FILE: Path = ROOT / os.getenv(
    "GOOGLE_CLIENT_SECRETS_FILE", "config/client_secrets.json"
)
GOOGLE_TOKEN_FILE: Path = ROOT / os.getenv(
    "GOOGLE_TOKEN_FILE", "config/token.json"
)
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")
CALENDAR_RAW_DIR: Path = RAW_FOLDER / "calendar"
CALENDAR_INTERIM_DIR: Path = INTERIM_FOLDER / "calendar"
