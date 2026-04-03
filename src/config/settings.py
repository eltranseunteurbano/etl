"""Configuración central del proyecto ETL.

Carga variables de entorno desde .env y expone rutas y parámetros
usados por todos los sub-pipelines.
"""

import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent.parent

SOURCES_FOLDER: Path = ROOT / "data" / "sources"
VENTAS_FOLDER: Path = SOURCES_FOLDER / "Ventas"
PELUQUERIA_FOLDER: Path = SOURCES_FOLDER / "Peluqueria"

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

# Sobreescribible con variables de entorno GOOGLE_CLIENT_SECRETS_FILE y
# GOOGLE_TOKEN_FILE si se necesita otra ubicación.
GOOGLE_CLIENT_SECRETS_FILE: Path = ROOT / os.getenv(
    "GOOGLE_CLIENT_SECRETS_FILE", "credentials/client_secrets.json"
)
GOOGLE_TOKEN_FILE: Path = ROOT / os.getenv(
    "GOOGLE_TOKEN_FILE", "credentials/token.json"
)
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "")
CALENDAR_RAW_DIR: Path = RAW_FOLDER / "calendar"
CALENDAR_INTERIM_DIR: Path = INTERIM_FOLDER / "calendar"


# ── Logging ──────────────────────────────────────────────────────────────────
def setup_logging() -> None:
    """Configura el logger raíz con un FileHandler diario en logs/.

    Solo añade el handler si el logger raíz no tiene ninguno todavía,
    para que sea seguro llamar esta función más de una vez.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"etl_{date.today().isoformat()}.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
        )
    )
    root.setLevel(logging.INFO)
    root.addHandler(handler)
