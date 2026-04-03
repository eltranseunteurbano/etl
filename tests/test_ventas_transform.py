"""Tests unitarios para src/ventas/transform.py."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ventas.constants import COLS_VENTAS_OUT
from src.ventas.transform import _clean_ventas_month, _year_month_from_filename

# ── _year_month_from_filename ────────────────────────────────────────────────


def test_year_month_enero():
    year, month = _year_month_from_filename(Path("2024_ENERO.csv"))
    assert year == 2024
    assert month == 1


def test_year_month_diciembre():
    _, month = _year_month_from_filename(Path("2023_DICIEMBRE.csv"))
    assert month == 12


def test_year_month_todos_los_meses():
    nombres = [
        "ENERO",
        "FEBRERO",
        "MARZO",
        "ABRIL",
        "MAYO",
        "JUNIO",
        "JULIO",
        "AGOSTO",
        "SEPTIEMBRE",
        "OCTUBRE",
        "NOVIEMBRE",
        "DICIEMBRE",
    ]
    for i, nombre in enumerate(nombres, 1):
        _, month = _year_month_from_filename(Path(f"2025_{nombre}.csv"))
        assert month == i, f"Fallo en mes {nombre}"


def test_year_month_filename_invalido_lanza_error():
    with pytest.raises(ValueError):
        _year_month_from_filename(Path("sin_guion.csv"))


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_ventas_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DIA": [1, 2, 3, 4],
            "VENTAS ALMACÉN ANTES IVA": [100.0, 200.0, 0.0, 150.0],
            "IVA": [19.0, 38.0, 0.0, 28.5],
            "VENTAS TOTAL ALMACÉN": [119.0, 238.0, 0.0, 178.5],
            "TOTAL VENTAS DÍA": [130.0, 250.0, 0.0, 190.0],
            "PELUQUERÍA": [11.0, 12.0, 0.0, 13.0],
        }
    )


# ── _clean_ventas_month ──────────────────────────────────────────────────────


def test_clean_ventas_columnas_salida():
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2024_ENERO.csv"))
    assert list(result.columns) == COLS_VENTAS_OUT


def test_clean_ventas_filtra_total_cero():
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2024_ENERO.csv"))
    # El día 3 tiene TOTAL VENTAS DÍA = 0 → debe eliminarse
    assert len(result) == 3


def test_clean_ventas_formato_fecha():
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2024_ENERO.csv"))
    assert result["FECHA"].iloc[0] == "01/01/2024"


def test_clean_ventas_renombra_columnas():
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2024_MARZO.csv"))
    assert "VENTAS_PRE" in result.columns
    assert "VENTAS_POST" in result.columns
    assert "VENTAS ALMACÉN ANTES IVA" not in result.columns
    assert "VENTAS TOTAL ALMACÉN" not in result.columns


def test_clean_ventas_columnas_faltantes_lanza_error():
    df = pd.DataFrame({"DIA": [1], "VENTAS ALMACÉN ANTES IVA": [100.0]})
    with pytest.raises(ValueError, match="faltan columnas"):
        _clean_ventas_month(df, Path("2024_ENERO.csv"))


def test_clean_ventas_columnas_numericas():
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2024_FEBRERO.csv"))
    for col in (
        "VENTAS_PRE",
        "IVA",
        "VENTAS_POST",
        "TOTAL VENTAS DÍA",
        "PELUQUERÍA",
    ):
        assert pd.api.types.is_numeric_dtype(result[col]), (
            f"{col} debería ser numérico"
        )


def test_clean_ventas_fecha_ultimo_mes():
    # Verifica que el mes correcto se usa para construir la fecha
    df = _make_ventas_df()
    result = _clean_ventas_month(df, Path("2025_DICIEMBRE.csv"))
    assert result["FECHA"].iloc[0] == "01/12/2025"
