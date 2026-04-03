"""Tests unitarios para src/calendar/transform.py."""

from __future__ import annotations

from src.calendar.constants import COLOR_MAP, FIELDS_TO_DROP
from src.calendar.transform import _clean, _flatten_dt

# ── _flatten_dt ──────────────────────────────────────────────────────────────


def test_flatten_dt_dict_con_datetime():
    value = {"dateTime": "2024-03-15T10:00:00-05:00"}
    assert _flatten_dt(value) == "2024-03-15T10:00:00-05:00"


def test_flatten_dt_dict_con_date():
    value = {"date": "2024-03-15"}
    assert _flatten_dt(value) == "2024-03-15"


def test_flatten_dt_string():
    assert _flatten_dt("2024-03-15") == "2024-03-15"


def test_flatten_dt_none():
    assert _flatten_dt(None) == ""


def test_flatten_dt_dict_vacio():
    assert _flatten_dt({}) == ""


# ── _clean ───────────────────────────────────────────────────────────────────


def _make_event(**kwargs) -> dict:
    base = {
        "id": "evt_001",
        "summary": "Cita Tobi",
        "start": {"dateTime": "2024-03-15T10:00:00-05:00"},
        "end": {"dateTime": "2024-03-15T11:00:00-05:00"},
    }
    base.update(kwargs)
    return base


def test_clean_elimina_campos_no_deseados():
    event = _make_event(
        kind="calendar#event", etag="abc", htmlLink="https://x"
    )
    result = _clean([event])
    for field in FIELDS_TO_DROP:
        assert field not in result[0], f"'{field}' debería eliminarse"


def test_clean_aplana_start_datetime():
    event = _make_event(start={"dateTime": "2024-03-15T10:00:00-05:00"})
    result = _clean([event])
    assert result[0]["start"] == "2024-03-15T10:00:00-05:00"


def test_clean_aplana_start_date():
    event = _make_event(start={"date": "2024-03-15"})
    result = _clean([event])
    assert result[0]["start"] == "2024-03-15"


def test_clean_mapea_color_conocido():
    event = _make_event(colorId="2")
    result = _clean([event])
    assert result[0]["color_label"] == COLOR_MAP["2"]
    assert result[0]["color_id"] == "2"


def test_clean_color_desconocido_es_none():
    event = _make_event(colorId="99")
    result = _clean([event])
    assert result[0]["color_label"] is None


def test_clean_sin_color_usa_cero():
    # Sin colorId → colorId="0" → usa COLOR_MAP["0"]
    event = _make_event()
    result = _clean([event])
    assert result[0]["color_id"] == "0"
    assert result[0]["color_label"] == COLOR_MAP["0"]


def test_clean_recurring_event_id():
    event = _make_event(recurringEventId="parent_abc")
    result = _clean([event])
    assert result[0]["recurrent_id"] == "parent_abc"


def test_clean_sin_recurring_event_id():
    event = _make_event()
    result = _clean([event])
    assert result[0]["recurrent_id"] is None


def test_clean_lista_vacia():
    assert _clean([]) == []


def test_clean_multiples_eventos():
    events = [_make_event(id=f"evt_{i}") for i in range(5)]
    result = _clean(events)
    assert len(result) == 5
