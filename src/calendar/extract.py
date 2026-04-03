"""Extracción de eventos desde Google Calendar API.

Soporta fetch completo (primera ejecución) y actualización incremental
basada en el timestamp guardado en data/state.json.
"""

from __future__ import annotations

import calendar
import datetime
import json
from collections.abc import Callable

from googleapiclient.discovery import build  # type: ignore[import]

from src.calendar.auth import get_credentials
from src.config.settings import (
    CALENDAR_RAW_DIR,
    GOOGLE_CALENDAR_ID,
    STATE_FILE,
)

_RAW_FILE = CALENDAR_RAW_DIR / "events.json"
_MAX_RESULTS = 2500


def _read_state() -> str | None:
    """Lee el último timestamp de ejecución desde state.json."""
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, encoding="utf-8") as f:
        state: dict = json.load(f)
    return state.get("calendar", {}).get("last_run")


def _end_of_month() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    last_day = calendar.monthrange(now.year, now.month)[1]
    return now.replace(
        day=last_day, hour=23, minute=59, second=59, microsecond=0
    ).isoformat()


def _fetch_all(
    service,
    time_min: str | None,
    on_log: Callable[[str], None],
) -> list[dict]:
    """Descarga todos los eventos paginando hasta agotar nextPageToken."""
    events: list[dict] = []
    page_token: str | None = None

    list_kwargs: dict = dict(
        calendarId=GOOGLE_CALENDAR_ID,
        alwaysIncludeEmail=False,
        singleEvents=True,
        orderBy="startTime",
        maxResults=_MAX_RESULTS,
        eventTypes=["default"],
        timeMax=_end_of_month(),
    )
    if time_min:
        list_kwargs["timeMin"] = time_min

    while True:
        list_kwargs["pageToken"] = page_token
        result = service.events().list(**list_kwargs).execute()
        batch: list[dict] = result.get("items", [])
        events.extend(batch)
        on_log(
            f"  Calendar: página {len(batch)} eventos"
            f" (acumulado: {len(events)})\n"
        )
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return events


def extract(
    *,
    on_progress: Callable[[int, str], None] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> None:
    """Descarga eventos del calendario y los guarda en data/raw/calendar/."""

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)
        else:
            print(msg, end="")

    def progress(pct: int, detail: str) -> None:
        if on_progress:
            on_progress(pct, detail)

    progress(5, "autenticando…")
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    last_run = _read_state()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    last_run_date = last_run[:10] if last_run else None

    CALENDAR_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Caché: si ya se ejecutó hoy, reutilizar el archivo raw
    if last_run_date == today and _RAW_FILE.exists():
        log(f"  Calendar: ya ejecutado hoy ({today}), usando caché\n")
        progress(44, f"caché ({today})")
        return

    if last_run and _RAW_FILE.exists():
        log(f"  Calendar: actualización incremental desde {last_run}\n")
        progress(12, "fetch incremental…")
        with open(_RAW_FILE, encoding="utf-8") as f:
            existing: list[dict] = json.load(f)
        new_events = _fetch_all(service, time_min=last_run, on_log=log)
        by_id = {e["id"]: e for e in existing}
        for e in new_events:
            by_id[e["id"]] = e
        events = list(by_id.values())
        log(
            f"  Calendar: {len(new_events)} nuevos/actualizados,"
            f" total {len(events)}\n"
        )
    else:
        log("  Calendar: primera ejecución, fetch completo\n")
        progress(12, "fetch completo…")
        events = _fetch_all(service, time_min=None, on_log=log)

    with open(_RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    log(f"  Calendar: {len(events)} eventos guardados en raw\n")
    progress(44, f"{len(events)} eventos")
