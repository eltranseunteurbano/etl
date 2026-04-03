"""Extracción de datos de peluquería desde archivos Excel anuales.
Lee los archivos YYYY.xlsx del directorio PELUQUERIA_DIR y los
persiste como CSV en data/raw/peluqueria_YYYY.csv.
Solo re-procesa archivos cuya fecha de modificación haya cambiado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config.settings import (
    PELUQUERIA_FOLDER,
    PELUQUERIA_RAW_DIR,
    STATE_FILE,
)

_HEADER_KEYWORDS = frozenset(
    {"nombre", "mascota", "raza", "servicio", "valor", "fecha"}
)


def _load_mtimes() -> dict[str, float]:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, encoding="utf-8") as f:
        state: dict = json.load(f)
    return state.get("peluqueria", {}).get("mtimes", {})


def _save_mtimes(mtimes: dict[str, float]) -> None:
    state: dict = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    state.setdefault("peluqueria", {})["mtimes"] = mtimes
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


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
    """Excel ``YYYY.xlsx`` en fuentes → ``peluqueria_YYYY.csv`` en raw.

    Omite archivos que no han cambiado desde la última ejecución
    (compara mtime del archivo fuente).
    """
    print("Extracting peluquería...")
    PELUQUERIA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    stored_mtimes = _load_mtimes()
    new_mtimes: dict[str, float] = dict(stored_mtimes)

    for path in sorted(PELUQUERIA_FOLDER.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        if not path.stem.isdigit():
            print(f"  Omitido (se espera YYYY.xlsx): {path.name}")
            continue

        mtime = path.stat().st_mtime
        if stored_mtimes.get(path.name) == mtime:
            print(f"  {path.name}: sin cambios, omitiendo extract")
            continue

        year = int(path.stem)
        df = _read_peluqueria_excel(path)
        out = PELUQUERIA_RAW_DIR / f"peluqueria_{year}.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  → raw/{out.name} ({len(df)} filas)")

        new_mtimes[path.name] = mtime

    _save_mtimes(new_mtimes)
