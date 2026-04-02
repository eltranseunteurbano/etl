"""Pipeline de ventas."""

from __future__ import annotations

from src.ventas.extract import extract
from src.ventas.load import load
from src.ventas.transform import transform


def pipeline() -> None:
    """Pipeline de ventas."""
    print("Running ventas pipeline...")
    extract()
    transform()
    load()
