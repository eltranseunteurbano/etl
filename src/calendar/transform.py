"""Transformación de eventos de Google Calendar.

Carga el JSON raw, descarta campos innecesarios, aplana fechas/horas,
mapea colores y guarda un CSV limpio en data/interim/calendar/.
"""

from __future__ import annotations

import json

import pandas as pd

from src.calendar.constants import COLOR_MAP, EVENTS_COLS, FIELDS_TO_DROP
from src.config.settings import CALENDAR_INTERIM_DIR, CALENDAR_RAW_DIR

_RAW_FILE = CALENDAR_RAW_DIR / "events.json"
_INTERIM_FILE = CALENDAR_INTERIM_DIR / "events.csv"


def _flatten_dt(value: dict | str | None) -> str:
    """Convierte el campo start/end (dict o str) a una cadena ISO plana."""
    if isinstance(value, dict):
        if "dateTime" in value:
            return value["dateTime"]
        return value.get("date", "")
    return value or ""


def _clean(events: list[dict]) -> list[dict]:
    clean: list[dict] = []
    for event in events:
        row = {k: v for k, v in event.items() if k not in FIELDS_TO_DROP}
        row["start"] = _flatten_dt(row.get("start"))
        row["end"] = _flatten_dt(row.get("end"))
        row["recurrent_id"] = event.get("recurringEventId")
        cid = str(event.get("colorId", "0"))
        row["color_label"] = COLOR_MAP.get(cid)
        row["color_id"] = cid
        clean.append(row)
    return clean


def transform() -> None:
    """Transforma events.json raw a events.csv interim."""
    with open(_RAW_FILE, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    clean = _clean(raw)

    rows = [
        {
            "id": e.get("id"),
            "summary": e.get("summary"),
            "description": e.get("description"),
            "location": e.get("location"),
            "color_label": e.get("color_label"),
            "recurrent_id": e.get("recurrent_id"),
            "color_id": e.get("color_id"),
            "start": e.get("start", ""),
            "end": e.get("end", ""),
            "created": e.get("created"),
            "updated": e.get("updated"),
        }
        for e in clean
    ]

    df = pd.DataFrame(rows, columns=EVENTS_COLS)
    CALENDAR_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_INTERIM_FILE, index=False, encoding="utf-8")
    print(f"  Calendar transform: {len(df)} eventos guardados en interim")
