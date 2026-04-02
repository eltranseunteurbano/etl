"""Pipeline de Alegra."""

from __future__ import annotations

from src.alegra.extract import extract
from src.alegra.load import load
from src.alegra.transform import transform


def pipeline() -> None:
    """Pipeline de Alegra."""
    print("Running alegra pipeline...")
    extract()
    transform()
    load()
