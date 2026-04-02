"""Pipeline de peluquería."""

from __future__ import annotations

from src.peluqueria.extract import extract
from src.peluqueria.load import load
from src.peluqueria.transform import transform


def pipeline() -> None:
    """Pipeline de peluquería."""
    print("Running peluquería pipeline...")
    extract()
    transform()
    load()
