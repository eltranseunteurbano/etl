"""Transformación de datos de Alegra.

Convierte los JSON crudos de la API en DataFrames normalizados
y los guarda como CSVs en data/interim/alegra/.
"""

from __future__ import annotations

import json

import pandas as pd

from src.alegra.constants import (
    CATEGORIAS_COLS,
    FACTURAS_COLS,
    ITEM_IDS_EXCLUIDOS,
    PRODUCTOS_COLS,
)
from src.config.settings import ALEGRA_INTERIM_DIR, ALEGRA_RAW_DIR


def _load_json(filename: str) -> list[dict]:
    path = ALEGRA_RAW_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_csv(df: pd.DataFrame, filename: str) -> None:
    ALEGRA_INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(ALEGRA_INTERIM_DIR / filename, index=False, encoding="utf-8")


def _transform_facturas(data: list[dict]) -> pd.DataFrame:
    """Una fila por línea de factura (desnormalizado)."""
    rows: list[dict] = []
    for inv in data:
        invoice_id = inv.get("id")
        fecha = inv.get("date") or inv.get("dueDate")
        total_factura = float(inv.get("total") or 0)
        client = inv.get("client") or {}
        cliente_id = client.get("id")

        for line in inv.get("items", []):
            taxes = line.get("tax") or []
            impuesto_pct = float(
                (taxes[0].get("percentage") if taxes else None) or 0
            )
            rows.append(
                {
                    "id": invoice_id,
                    "date": fecha,
                    "client_id": cliente_id,
                    "item_id": line.get("id"),
                    "item_name": line.get("name"),
                    "quantity": float(line.get("quantity") or 0),
                    "unit_price": float(line.get("price") or 0),
                    "tax_percentage": impuesto_pct,
                    "total_product": float(line.get("price") or 0)
                    * float(line.get("quantity") or 0),
                    "total": total_factura,
                }
            )

    df = pd.DataFrame(rows, columns=FACTURAS_COLS)
    excluidos = df["item_id"].isin([str(i) for i in ITEM_IDS_EXCLUIDOS])
    if excluidos.any():
        print(
            f"  Alegra transform: {excluidos.sum()} líneas excluidas "
            f"(item_ids: {ITEM_IDS_EXCLUIDOS})"
        )
        df = df[~excluidos].reset_index(drop=True)
    return df


def _transform_productos(data: list[dict]) -> pd.DataFrame:
    """Una fila por producto."""
    rows: list[dict] = []
    for item in data:
        raw_price = item.get("price") or []
        price_val = 0.0
        if isinstance(raw_price, list) and raw_price:
            price_val = float(raw_price[0].get("price") or 0)
        elif isinstance(raw_price, dict):
            price_val = float(raw_price.get("price") or 0)

        category = item.get("category") or {}
        categoria_id = (
            category.get("id") if isinstance(category, dict) else None
        )

        taxes = item.get("tax") or []
        iva_pct = float((taxes[0].get("percentage") if taxes else None) or 0)
        iva_val = round(price_val * iva_pct / 100, 2)

        rows.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "reference": item.get("reference"),
                "status": item.get("status"),
                "price": price_val,
                "category_id": categoria_id,
                "available_quantity": float(
                    (item.get("inventory") or {}).get("availableQuantity") or 0
                ),
                "iva_percentage": iva_pct,
                "iva": iva_val,
            }
        )

    return pd.DataFrame(rows)


def _transform_categorias(data: list[dict]) -> pd.DataFrame:
    """Una fila por categoría."""
    rows = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "status": c.get("status"),
        }
        for c in data
    ]
    return pd.DataFrame(rows, columns=CATEGORIAS_COLS)


def transform() -> None:
    """Transforma los JSON raw de Alegra a CSVs interim."""
    df_facturas = _transform_facturas(_load_json("facturas.json"))
    _save_csv(df_facturas, "facturas.csv")
    print(f"  Alegra transform: {len(df_facturas)} líneas de factura")

    agg = (
        df_facturas.groupby("item_id")
        .agg(
            total_sold_quantity=("quantity", "sum"),
            total_revenue=("total_product", "sum"),
        )
        .reset_index()
        .rename(columns={"item_id": "id"})
    )
    ids_excluidos = [str(i) for i in ITEM_IDS_EXCLUIDOS]
    df_productos = (
        _transform_productos(_load_json("productos.json"))
        .merge(agg, on="id", how="left")
        .fillna({"total_sold_quantity": 0.0, "total_revenue": 0.0})[
            PRODUCTOS_COLS
        ]
    )
    mask_prod = df_productos["id"].isin(ids_excluidos)
    if mask_prod.any():
        print(
            f"  Alegra transform: {mask_prod.sum()} productos excluidos "
            f"(item_ids: {ITEM_IDS_EXCLUIDOS})"
        )
        df_productos = df_productos[~mask_prod].reset_index(drop=True)
    _save_csv(df_productos, "productos.csv")
    print(f"  Alegra transform: {len(df_productos)} productos")

    df_categorias = _transform_categorias(_load_json("categorias.json"))
    _save_csv(df_categorias, "categorias.csv")
    print(f"  Alegra transform: {len(df_categorias)} categorías")
