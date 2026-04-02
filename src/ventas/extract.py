"""Extracción de datos de ventas desde archivos Excel anuales.

Lee los archivos YYYY.xlsx del directorio VENTAS_FOLDER y los
persiste como CSV mensuales en data/raw/ventas/YYYY_MES.csv.
"""

from __future__ import annotations

import pandas as pd

from src.config.settings import VENTAS_FOLDER, VENTAS_RAW_DIR
from src.ventas.constants import MONTH_SHEETS


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
