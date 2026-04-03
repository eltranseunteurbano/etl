"""Tests unitarios para src/alegra/transform.py."""

from __future__ import annotations

import pandas as pd

from src.alegra.constants import CATEGORIAS_COLS, FACTURAS_COLS
from src.alegra.transform import (
    _transform_categorias,
    _transform_facturas,
    _transform_productos,
)

# ── fixtures ─────────────────────────────────────────────────────────────────


def _factura(item_count: int = 1) -> dict:
    items = [
        {
            "id": 100 + i,
            "name": f"Producto {i}",
            "quantity": float(i + 1),
            "price": 50000.0,
            "tax": [{"percentage": 19}],
        }
        for i in range(item_count)
    ]
    return {
        "id": 1,
        "date": "2024-03-01",
        "total": 119000.0,
        "client": {"id": 10},
        "items": items,
    }


def _producto() -> dict:
    return {
        "id": 100,
        "name": "Shampoo",
        "reference": "REF-001",
        "status": "active",
        "price": [{"price": 50000.0}],
        "category": {"id": 5},
        "tax": [{"percentage": 19}],
        "inventory": {"availableQuantity": 10.0},
    }


# ── _transform_facturas ──────────────────────────────────────────────────────


def test_facturas_columnas_salida():
    df = _transform_facturas([_factura()])
    assert list(df.columns) == FACTURAS_COLS


def test_facturas_desnormaliza_items():
    # 1 factura con 2 items → 2 filas, mismo id de factura
    df = _transform_facturas([_factura(item_count=2)])
    assert len(df) == 2
    assert (df["id"] == 1).all()


def test_facturas_vacia():
    df = _transform_facturas([])
    assert len(df) == 0
    assert list(df.columns) == FACTURAS_COLS


def test_facturas_impuesto_extraido():
    df = _transform_facturas([_factura()])
    assert df["tax_percentage"].iloc[0] == 19.0


def test_facturas_sin_impuesto_es_cero():
    factura = _factura()
    factura["items"][0]["tax"] = []
    df = _transform_facturas([factura])
    assert df["tax_percentage"].iloc[0] == 0.0


def test_facturas_total_product():
    # price=50000, quantity=1 → total_product=50000
    df = _transform_facturas([_factura()])
    assert df["total_product"].iloc[0] == 50000.0


def test_facturas_multiples_facturas():
    f1 = _factura()
    f1["id"] = 1
    f2 = _factura()
    f2["id"] = 2
    df = _transform_facturas([f1, f2])
    assert len(df) == 2
    assert set(df["id"]) == {1, 2}


def test_facturas_cliente_nulo():
    factura = _factura()
    factura["client"] = None
    df = _transform_facturas([factura])
    assert pd.isna(df["client_id"].iloc[0])


# ── _transform_productos ─────────────────────────────────────────────────────


def test_productos_iva_calculado():
    # price=50000, iva_pct=19 → iva=9500
    df = _transform_productos([_producto()])
    assert df["iva"].iloc[0] == 9500.0


def test_productos_price_desde_lista():
    df = _transform_productos([_producto()])
    assert df["price"].iloc[0] == 50000.0


def test_productos_price_desde_dict():
    prod = _producto()
    prod["price"] = {"price": 20000.0}
    df = _transform_productos([prod])
    assert df["price"].iloc[0] == 20000.0


def test_productos_sin_impuesto():
    prod = _producto()
    prod["tax"] = []
    df = _transform_productos([prod])
    assert df["iva_percentage"].iloc[0] == 0.0
    assert df["iva"].iloc[0] == 0.0


def test_productos_sin_precio_es_cero():
    prod = _producto()
    prod["price"] = []
    df = _transform_productos([prod])
    assert df["price"].iloc[0] == 0.0


def test_productos_categoria_nula():
    prod = _producto()
    prod["category"] = None
    df = _transform_productos([prod])
    assert pd.isna(df["category_id"].iloc[0])


# ── _transform_categorias ────────────────────────────────────────────────────


def test_categorias_columnas_salida():
    data = [{"id": 5, "name": "Higiene", "status": "active"}]
    df = _transform_categorias(data)
    assert list(df.columns) == CATEGORIAS_COLS


def test_categorias_valores():
    data = [{"id": 5, "name": "Higiene", "status": "active"}]
    df = _transform_categorias(data)
    assert df["id"].iloc[0] == 5
    assert df["name"].iloc[0] == "Higiene"
    assert df["status"].iloc[0] == "active"


def test_categorias_vacia():
    df = _transform_categorias([])
    assert len(df) == 0
    assert list(df.columns) == CATEGORIAS_COLS
