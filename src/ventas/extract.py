"""Extracción de datos de ventas desde archivos Excel anuales.

Lee los archivos YYYY.xlsx del directorio VENTAS_FOLDER y los
persiste como CSV mensuales en data/raw/ventas/YYYY_MES.csv.
Solo re-procesa archivos cuya fecha de modificación haya cambiado.
"""

from __future__ import annotations

import json

import pandas as pd

from src.config.settings import STATE_FILE, VENTAS_FOLDER, VENTAS_RAW_DIR
from src.ventas.constants import MONTH_SHEETS


def _load_mtimes() -> dict[str, float]:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, encoding="utf-8") as f:
        state: dict = json.load(f)
    return state.get("ventas", {}).get("mtimes", {})


def _save_mtimes(mtimes: dict[str, float]) -> None:
    state: dict = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    state.setdefault("ventas", {})["mtimes"] = mtimes
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── Main functions ───────────────────────────────────────────────────────────
def extract() -> None:
    """Lee Excel de fuentes; un CSV por mes en data/raw/ventas/.

    Omite archivos que no han cambiado desde la última ejecución
    (compara mtime del archivo fuente).
    """
    print("Extracting ventas diarias...")
    VENTAS_RAW_DIR.mkdir(parents=True, exist_ok=True)

    stored_mtimes = _load_mtimes()
    new_mtimes: dict[str, float] = dict(stored_mtimes)

    for file in sorted(VENTAS_FOLDER.glob("*.xlsx")):
        if file.name.startswith("~$"):
            continue
        if not file.stem.isdigit():
            print(f"  Omitido (nombre sin año): {file.name}")
            continue

        mtime = file.stat().st_mtime
        if stored_mtimes.get(file.name) == mtime:
            print(f"  {file.name}: sin cambios, omitiendo extract")
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

        new_mtimes[file.name] = mtime

    _save_mtimes(new_mtimes)
