"""Pipeline ETL de servicios de peluquería.

Un Excel por año en fuentes → CSV en raw → limpieza en interim → tabla
``peluqueria`` en SQLite y ``processed/peluqueria.csv``.

La primera columna del Excel ya trae la fecha completa del registro.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config.settings import (
    DATABASE_PATH,
    PELUQUERIA_FOLDER,
    PELUQUERIA_INTERIM_DIR,
    PELUQUERIA_RAW_DIR,
    PROCESSED_FOLDER,
)

_HEADER_KEYWORDS = frozenset(
    {"nombre", "mascota", "raza", "servicio", "valor", "fecha"}
)

COLS_PELUQUERIA = [
    "FECHA",
    "NOMBRE DEL PROPIETARIO",
    "MASCOTA",
    "RAZA",
    "SERVICIO",
    "ADICIONALES",
    "PELO",
    "VALOR",
    "PESO",
    "ACCESORIO",
]


def _read_peluqueria_excel(path: Path) -> pd.DataFrame:
    """Lee el Excel anual; detecta la fila de encabezado."""
    probe = pd.read_excel(path, header=None, nrows=15, engine="openpyxl")
    header_row = 0
    for idx, row in probe.iterrows():
        cells = {str(v).strip().lower() for v in row if pd.notna(v)}
        if _HEADER_KEYWORDS & cells:
            header_row = int(idx)
            break
    df = pd.read_excel(path, header=header_row, engine="openpyxl")
    return df.dropna(how="all")


def _clean_peluqueria(df: pd.DataFrame) -> pd.DataFrame:
    """Primera columna → FECHA; solo COLS_PELUQUERIA; fecha DD/MM/AAAA."""
    out = df.copy()
    first = out.columns[0]
    out = out.rename(columns={first: "FECHA"})
    missing = [c for c in COLS_PELUQUERIA if c not in out.columns]
    if missing:
        msg = f"Faltan columnas en peluquería: {missing}"
        raise ValueError(msg)
    out = out[COLS_PELUQUERIA].copy()
    out["FECHA"] = pd.to_datetime(out["FECHA"], dayfirst=True, errors="coerce")
    out = out.loc[out["FECHA"].notna()].copy()
    out["FECHA"] = out["FECHA"].dt.strftime("%d/%m/%Y")
    return out


def extract() -> None:
    """Excel ``YYYY.xlsx`` en fuentes → ``peluqueria_YYYY.csv`` en raw."""
    print("Extracting peluquería...")
    PELUQUERIA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for path in sorted(PELUQUERIA_FOLDER.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        if not path.stem.isdigit():
            print(f"  Omitido (se espera YYYY.xlsx): {path.name}")
            continue
        year = int(path.stem)
        df = _read_peluqueria_excel(path)
        out = PELUQUERIA_RAW_DIR / f"peluqueria_{year}.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  → raw/{out.name} ({len(df)} filas)")


def transform() -> None:
    """Lee raw, normaliza FECHA, escribe interim con el mismo nombre."""
    print("Transforming peluquería...")
    PELUQUERIA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    paths = sorted(PELUQUERIA_RAW_DIR.glob("peluqueria_*.csv"))
    if not paths:
        print("  No hay CSV en raw/peluqueria.")
        return

    for path in paths:
        df = pd.read_csv(path, encoding="utf-8")
        out = _clean_peluqueria(df)
        dest = PELUQUERIA_INTERIM_DIR / path.name
        out.to_csv(dest, index=False, encoding="utf-8")
        print(f"  → interim/{dest.name} ({len(out)} filas)")


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


def pipeline() -> None:
    """Pipeline peluquería."""
    print("Running peluquería pipeline...")
    extract()
    transform()
    load()
