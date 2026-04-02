"""Transformación de datos de ventas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config.settings import VENTAS_INTERIM_DIR, VENTAS_RAW_DIR
from src.ventas.constants import (
    COLS_VENTAS_KEEP,
    COLS_VENTAS_OUT,
    MONTH_NAME_TO_NUM,
)


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
