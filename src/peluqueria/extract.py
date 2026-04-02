"""Extracción de datos de peluquería desde archivos Excel anuales.
Lee los archivos YYYY.xlsx del directorio PELUQUERIA_DIR y los
persiste como CSV en data/raw/peluqueria_YYYY.csv. Soporta
extracción histórica (todos los años) e incremental (desde un
año específico).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config.settings import PELUQUERIA_FOLDER, PELUQUERIA_RAW_DIR

_HEADER_KEYWORDS = frozenset(
    {"nombre", "mascota", "raza", "servicio", "valor", "fecha"}
)


# ── Utilities functions ──────────────────────────────────────────────────────
def _read_peluqueria_excel(path: Path) -> pd.DataFrame:
    """Lee el Excel anual; detecta la fila de encabezado."""
    probe = pd.read_excel(path, header=None, nrows=15, engine="openpyxl")
    header_row = 0
    for i, (_, row) in enumerate(probe.iterrows()):
        cells = {str(v).strip().lower() for v in row if pd.notna(v)}
        if _HEADER_KEYWORDS & cells:
            header_row = i
            break
    df = pd.read_excel(path, header=header_row, engine="openpyxl")
    return df.dropna(how="all")


# ── Main functions ───────────────────────────────────────────────────────────
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
