"""Carga de datos de peluquería en la base de datos SQLite."""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.config.settings import (
    DATABASE_PATH,
    PELUQUERIA_INTERIM_DIR,
    PROCESSED_FOLDER,
)


# ── Main functions ───────────────────────────────────────────────────────────
def load() -> None:
    """Concat interim, orden FECHA, CSV processed y SQLite."""
    print("Loading peluquería...")

    paths = sorted(PELUQUERIA_INTERIM_DIR.glob("peluqueria_*.csv"))
    if not paths:
        print("  No hay CSV en interim/peluqueria.")
        return

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
        PROCESSED_FOLDER / "peluqueria.csv",
        index=False,
        encoding="utf-8",
    )

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        combined.to_sql("peluqueria", conn, if_exists="replace", index=False)
    n = len(combined)
    print(f"  → processed/peluqueria.csv, SQLite peluqueria ({n} filas)")
