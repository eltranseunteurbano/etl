"""Carga de eventos de Google Calendar en SQLite y actualización de estado."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

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
    state.setdefault("calendar", {})["last_run"] = datetime.now(
        timezone.utc
    ).isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load() -> str:
    """Carga events.csv en SQLite y actualiza state.json.

    Returns:
        Resumen corto de lo cargado (para monitor / logs).
    """
    df = pd.read_csv(_INTERIM_FILE, encoding="utf-8")
    df["_etl_loaded_at"] = datetime.now(timezone.utc).isoformat()

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        df.to_sql("calendar_events", conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_events_id"
            " ON calendar_events(id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_events_start"
            " ON calendar_events(start)"
        )
        print(f"  Calendar load: {len(df)} eventos en SQLite")

    _update_state()
    print("  Calendar load: state.json actualizado")
    return f"{len(df)} eventos"
