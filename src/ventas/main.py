"""Pipeline ETL de ventas diarias.

Define extracción, transformación y carga para el pipeline de ventas diarias.
La función de entrada pública es :func:`pipeline`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config.settings import (
    DATABASE_PATH,
    PROCESSED_FOLDER,
    VENTAS_FOLDER,
    VENTAS_INTERIM_DIR,
    VENTAS_RAW_DIR,
)

# ── Constants ───────────────────────────────────────────────────────────────
MONTH_SHEETS = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]

MONTH_NAME_TO_NUM: dict[str, int] = {
    name: i + 1 for i, name in enumerate(MONTH_SHEETS)
}

# Nombres como en el Excel/CSV exportado (origen)
COLS_VENTAS_KEEP = [
    "VENTAS ALMACÉN ANTES IVA",
    "IVA",
    "VENTAS TOTAL ALMACÉN",
    "TOTAL VENTAS DÍA",
    "PELUQUERÍA",
]

# Orden final en interim / SQLite
COLS_VENTAS_OUT = [
    "FECHA",
    "VENTAS_PRE",
    "IVA",
    "VENTAS_POST",
    "TOTAL VENTAS DÍA",
    "PELUQUERÍA",
]


# ── Utilities functions ──────────────────────────────────────────────────────
def _year_month_from_filename(csv_path: Path) -> tuple[int, int]:
    stem = csv_path.stem
    if "_" not in stem:
        msg = f"Se esperaba YYYY_MES.csv, recibido: {csv_path.name}"
        raise ValueError(msg)
    year_s, month_name = stem.split("_", 1)
    return int(year_s), MONTH_NAME_TO_NUM[month_name]


def _clean_ventas_month(df: pd.DataFrame, csv_path: Path) -> pd.DataFrame:
    """Mantiene columnas clave, añade fecha y quita días con total 0."""
    year, month_num = _year_month_from_filename(csv_path)
    out = df.copy()

    day_col = out.columns[0]
    missing = [c for c in COLS_VENTAS_KEEP if c not in out.columns]
    if missing:
        msg = f"{csv_path.name}: faltan columnas {missing}"
        raise ValueError(msg)

    total = pd.to_numeric(out["TOTAL VENTAS DÍA"], errors="coerce").fillna(0)
    out = out.loc[total != 0].copy()

    day = pd.to_numeric(out[day_col], errors="coerce")
    out = out.loc[day.notna()].copy()
    day = pd.to_numeric(out[day_col], errors="coerce").astype(int)

    ts = pd.to_datetime(
        {"year": year, "month": month_num, "day": day},
        errors="coerce",
    )
    out = out.loc[ts.notna()].copy()
    day = pd.to_numeric(out[day_col], errors="coerce").astype(int)
    ts = pd.to_datetime(
        {"year": year, "month": month_num, "day": day},
        errors="coerce",
    )
    out["FECHA"] = ts.dt.strftime("%d/%m/%Y")

    out = out[COLS_VENTAS_KEEP + ["FECHA"]]

    out["VENTAS ALMACÉN ANTES IVA"] = pd.to_numeric(
        out["VENTAS ALMACÉN ANTES IVA"],
        errors="coerce",
    )
    out["IVA"] = pd.to_numeric(out["IVA"], errors="coerce")
    out["VENTAS TOTAL ALMACÉN"] = pd.to_numeric(
        out["VENTAS TOTAL ALMACÉN"],
        errors="coerce",
    )
    out["TOTAL VENTAS DÍA"] = pd.to_numeric(
        out["TOTAL VENTAS DÍA"],
        errors="coerce",
    )
    out["PELUQUERÍA"] = pd.to_numeric(out["PELUQUERÍA"], errors="coerce")

    out = out.rename(
        columns={
            "VENTAS ALMACÉN ANTES IVA": "VENTAS_PRE",
            "VENTAS TOTAL ALMACÉN": "VENTAS_POST",
        },
    )
    return out[COLS_VENTAS_OUT]


# ── Main functions ───────────────────────────────────────────────────────────
def extract() -> None:
    """Lee Excel de fuentes; un CSV por mes en data/raw/ventas/."""
    print("Extracting ventas diarias...")
    VENTAS_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for file in sorted(VENTAS_FOLDER.glob("*.xlsx")):
        if file.name.startswith("~$"):
            continue
        if not file.stem.isdigit():
            print(f"  Omitido (nombre sin año): {file.name}")
            continue
        year = int(file.stem)

        all_sheets = pd.read_excel(file, sheet_name=None, engine="openpyxl")
        months_wanted = [m for m in MONTH_SHEETS if m in all_sheets]
        months_missing = [m for m in MONTH_SHEETS if m not in all_sheets]
        if months_missing:
            print(f"  {file.name}: sin hojas (año parcial?): {months_missing}")
        sheets = {name: all_sheets[name] for name in months_wanted}
        shapes = {name: df.shape for name, df in sheets.items()}
        print(file.name, shapes)

        for month_name, df in sheets.items():
            out_path = VENTAS_RAW_DIR / f"{year}_{month_name}.csv"
            df.to_csv(out_path, index=False, encoding="utf-8")
            print(f"  → raw/{out_path.name}")


def transform() -> None:
    """Lee CSV en raw, aplica clean_ventas_month, escribe en interim."""
    print("Transforming ventas diarias...")
    VENTAS_INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    paths = sorted(VENTAS_RAW_DIR.glob("*.csv"))
    if not paths:
        print("  No hay CSV en raw/ventas; nada que transformar.")
        return

    for path in paths:
        df = pd.read_csv(path, encoding="utf-8")
        out = _clean_ventas_month(df, path)
        out_path = VENTAS_INTERIM_DIR / path.name
        out.to_csv(out_path, index=False, encoding="utf-8")
        print(f"  → interim/{out_path.name} ({out.shape[0]} filas)")


def load() -> None:
    """Concatena CSV de interim y reemplaza la tabla ``ventas`` en SQLite."""
    print("Loading ventas diarias...")

    paths = sorted(VENTAS_INTERIM_DIR.glob("*.csv"))
    if not paths:
        print("  No hay CSV en interim/ventas; no se actualiza la base.")
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
        PROCESSED_FOLDER / "ventas.csv",
        index=False,
        encoding="utf-8",
    )

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        combined.to_sql("ventas", conn, if_exists="replace", index=False)
    print(f"  → {DATABASE_PATH.name} tabla ventas ({len(combined)} filas)")


def pipeline() -> None:
    """Pipeline de ventas."""
    print("Running ventas pipeline...")
    extract()
    transform()
    load()
