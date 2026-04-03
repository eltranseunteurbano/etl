"""Carga de datos de Alegra en SQLite y actualización de estado."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

import pandas as pd

from src.config.settings import (
    ALEGRA_INTERIM_DIR,
    DATABASE_PATH,
    STATE_FILE,
)


def _load_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(ALEGRA_INTERIM_DIR / filename, encoding="utf-8")


def _update_state() -> None:
    state: dict = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    state.setdefault("alegra", {})["last_invoice_date"] = (
        date.today().isoformat()
    )
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load() -> str:
    """Carga CSVs interim de Alegra en SQLite y actualiza state.json.

    Returns:
        Resumen corto de lo cargado (para monitor / logs).
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    df_facturas = _load_csv("facturas.csv")
    df_productos = _load_csv("productos.csv")
    df_categorias = _load_csv("categorias.csv")

    with sqlite3.connect(DATABASE_PATH) as conn:
        # Facturas: append solo las nuevas (sin duplicados)
        df_facturas.to_sql(
            "alegra_facturas", conn, if_exists="replace", index=False
        )
        print(f"  Alegra load: {len(df_facturas)} facturas")

        # Productos y categorías: siempre frescos
        df_productos.to_sql(
            "alegra_productos", conn, if_exists="replace", index=False
        )
        print(f"  Alegra load: {len(df_productos)} productos")

        df_categorias.to_sql(
            "alegra_categorias", conn, if_exists="replace", index=False
        )
        print(f"  Alegra load: {len(df_categorias)} categorías")

    _update_state()
    print(
        f"  Alegra load: state.json actualizado ({date.today().isoformat()})"
    )
    return (
        f"{len(df_facturas)} facturas, "
        f"{len(df_productos)} productos, "
        f"{len(df_categorias)} categorías"
    )
