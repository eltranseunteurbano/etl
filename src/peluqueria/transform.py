"""Transformación de datos de peluquería."""

from __future__ import annotations

import pandas as pd

from src.config.settings import PELUQUERIA_INTERIM_DIR, PELUQUERIA_RAW_DIR
from src.peluqueria.constants import (
    COLS_PELUQUERIA,
    COLS_PELUQUERIA_CATEGORICAS,
)


# ── Utilities functions ──────────────────────────────────────────────────────
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
    out["FECHA"] = out["FECHA"].dt.strftime("%Y-%m-%d")
    out = _apply_categoricas_peluqueria(out)
    return out


def _apply_categoricas_peluqueria(df: pd.DataFrame) -> pd.DataFrame:
    """Strip, vacíos → NA, dtype category en columnas de dimensión."""
    out = df.copy()
    for col in COLS_PELUQUERIA_CATEGORICAS:
        s = out[col].astype("string").str.strip()
        s = s.replace("", pd.NA)
        out[col] = s.astype("category")
    return out


# ── Main functions ───────────────────────────────────────────────────────────
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
