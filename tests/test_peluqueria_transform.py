"""Tests unitarios para src/peluqueria/transform.py."""

from __future__ import annotations

import pandas as pd
import pytest

from src.peluqueria.constants import (
    COLS_PELUQUERIA,
    COLS_PELUQUERIA_CATEGORICAS,
)
from src.peluqueria.transform import (
    _apply_categoricas_peluqueria,
    _clean_peluqueria,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_peluqueria_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "FECHA": [
                "01/03/2024",
                "15/03/2024",
                "fecha_invalida",
                "20/03/2024",
            ],
            "NOMBRE DEL PROPIETARIO": ["Ana", "  Carlos  ", "X", "Luisa"],
            "MASCOTA": ["Tobi", "Luna", "Max", "Kira"],
            "RAZA": ["Poodle", "Labrador", "Bulldog", "Shih Tzu"],
            "SERVICIO": ["Baño", "Corte", "Baño", "Corte"],
            "ADICIONALES": ["", "Uñas", "", ""],
            "PELO": ["Corto", "Largo", "Mediano", "Corto"],
            "VALOR": [30000, 45000, 30000, 35000],
            "PESO": [5.0, 10.0, 15.0, 4.0],
            "ACCESORIO": ["", "Lazo", "", ""],
        }
    )


# ── _clean_peluqueria ────────────────────────────────────────────────────────


def test_clean_peluqueria_columnas_salida():
    df = _make_peluqueria_df()
    result = _clean_peluqueria(df)
    assert list(result.columns) == COLS_PELUQUERIA


def test_clean_peluqueria_descarta_fechas_invalidas():
    df = _make_peluqueria_df()
    result = _clean_peluqueria(df)
    # "fecha_invalida" debe eliminarse → 3 filas válidas
    assert len(result) == 3


def test_clean_peluqueria_formato_fecha_iso():
    df = _make_peluqueria_df()
    result = _clean_peluqueria(df)
    # Debe guardarse en formato ISO YYYY-MM-DD
    assert result["FECHA"].iloc[0] == "2024-03-01"


def test_clean_peluqueria_fecha_no_invierte_dia_mes():
    """Día 15 no puede confundirse con mes 15: el mes debe seguir siendo 03."""
    df = _make_peluqueria_df()
    result = _clean_peluqueria(df)
    # Fila 1 es "15/03/2024" → YYYY-MM-DD debe ser "2024-03-15", no "2024-15-03"
    assert result["FECHA"].iloc[1] == "2024-03-15"


def test_clean_peluqueria_columnas_faltantes_lanza_error():
    df = pd.DataFrame({"FECHA": ["01/03/2024"], "MASCOTA": ["Tobi"]})
    with pytest.raises(ValueError, match="Faltan columnas"):
        _clean_peluqueria(df)


def test_clean_peluqueria_primera_columna_renombrada():
    df = _make_peluqueria_df().rename(columns={"FECHA": "Fecha Cita"})
    # La función toma la primera columna como FECHA independientemente del nombre
    result = _clean_peluqueria(df)
    assert "FECHA" in result.columns


# ── _apply_categoricas_peluqueria ────────────────────────────────────────────


def test_categoricas_dtype_es_category():
    df = _make_peluqueria_df()
    result = _apply_categoricas_peluqueria(df)
    for col in COLS_PELUQUERIA_CATEGORICAS:
        assert result[col].dtype.name == "category", (
            f"{col} debería ser dtype category"
        )


def test_categoricas_strip_espacios():
    df = _make_peluqueria_df()
    result = _apply_categoricas_peluqueria(df)
    categorias = result["NOMBRE DEL PROPIETARIO"].cat.categories.tolist()
    assert "Carlos" in categorias
    assert "  Carlos  " not in categorias


def test_categoricas_vacios_a_na():
    df = _make_peluqueria_df()
    result = _apply_categoricas_peluqueria(df)
    # Las celdas vacías ("") deben convertirse a pd.NA
    assert result["ADICIONALES"].isna().any()
    assert result["ACCESORIO"].isna().any()
