"""Carga de eventos de Google Calendar en SQLite y actualización de estado."""

from __future__ import annotations

import datetime
import json
import sqlite3

import pandas as pd

from src.config.settings import (
    CALENDAR_INTERIM_DIR,
    DATABASE_PATH,
    STATE_FILE,
)

_INTERIM_FILE = CALENDAR_INTERIM_DIR / "events.csv"


def _update_state() -> None:
    state: dict = {}
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    state.setdefault("calendar", {})["last_run"] = (
        datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load() -> str:
    """Carga events.csv en SQLite y actualiza state.json.

    Returns:
        Resumen corto de lo cargado (para monitor / logs).
    """
    df = pd.read_csv(_INTERIM_FILE, encoding="utf-8")

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        df.to_sql("calendar_events", conn, if_exists="replace", index=False)
        print(f"  Calendar load: {len(df)} eventos en SQLite")

    _update_state()
    print("  Calendar load: state.json actualizado")
    return f"{len(df)} eventos"
