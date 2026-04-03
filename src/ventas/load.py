"""Carga de datos de ventas en la base de datos SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pandas as pd

from src.config.settings import (
    DATABASE_PATH,
    PROCESSED_FOLDER,
    VENTAS_INTERIM_DIR,
)


# ── Main functions ───────────────────────────────────────────────────────────
def load() -> int | None:
    """Concatena CSV de interim y reemplaza la tabla ``ventas`` en SQLite.

    Returns:
        Número de filas cargadas, o ``None`` si no había datos.
    """
    print("Loading ventas diarias...")

    paths = sorted(VENTAS_INTERIM_DIR.glob("*.csv"))
    if not paths:
        print("  No hay CSV en interim/ventas; no se actualiza la base.")
        return None

    dfs = [pd.read_csv(p, encoding="utf-8") for p in paths]
    combined = pd.concat(dfs, ignore_index=True)
    combined["FECHA"] = pd.to_datetime(
        combined["FECHA"], dayfirst=True, errors="coerce"
    )
    combined = combined.sort_values(by="FECHA").reset_index(drop=True)

    PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)
    export = combined.copy()
    export["FECHA"] = export["FECHA"].dt.strftime("%d/%m/%Y")
    export.to_csv(
        PROCESSED_FOLDER / "ventas.csv",
        index=False,
        encoding="utf-8",
    )

    combined["_etl_loaded_at"] = datetime.now(timezone.utc).isoformat()

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        combined.to_sql("ventas", conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ventas_fecha"
            " ON ventas(FECHA)"
        )
    n = len(combined)
    print(f"  → {DATABASE_PATH.name} tabla ventas ({n} filas)")
    return n
