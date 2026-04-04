"""Constantes del pipeline Alegra."""

from __future__ import annotations

# IDs de items que son servicios registrados como productos y deben
# excluirse de las líneas de factura durante el transform.
# Agrega aquí nuevos IDs cuando los identifiques.
ITEM_IDS_EXCLUIDOS: list[int] = [2555, 1]

FACTURAS_COLS: list[str] = [
    "id",
    "date",
    "client_id",
    "item_id",
    "item_name",
    "quantity",
    "unit_price",
    "tax_percentage",
    "total_product",
    "total",
]

PRODUCTOS_COLS: list[str] = [
    "id",
    "name",
    "reference",
    "status",
    "price",
    "category_id",
    "available_quantity",
    "iva_percentage",
    "iva",
    "total_sold_quantity",
    "total_revenue",
]

CATEGORIAS_COLS: list[str] = [
    "id",
    "name",
    "status",
]
