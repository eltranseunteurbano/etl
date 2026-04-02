"""Constantes del pipeline Alegra."""

from __future__ import annotations

FACTURAS_COLS: list[str] = [
    "invoice_id",
    "fecha",
    "cliente_id",
    "cliente_nombre",
    "item_id",
    "item_nombre",
    "cantidad",
    "precio_unitario",
    "impuesto_pct",
    "total_factura",
]

PRODUCTOS_COLS: list[str] = [
    "item_id",
    "nombre",
    "referencia",
    "estado",
    "precio",
    "categoria_id",
]

CATEGORIAS_COLS: list[str] = [
    "categoria_id",
    "nombre",
]
