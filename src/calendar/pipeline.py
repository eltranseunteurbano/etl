"""Pipeline de Google Calendar."""

from __future__ import annotations

from src.calendar.extract import extract
from src.calendar.load import load
from src.calendar.transform import transform


def pipeline() -> None:
    """Pipeline de Google Calendar."""
    print("Running calendar pipeline...")
    extract()
    transform()
    load()
