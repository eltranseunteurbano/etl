"""Esquema de columnas esperado para datos de ventas."""

MONTH_SHEETS = [
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

MONTH_NAME_TO_NUM: dict[str, int] = {
    name: i + 1 for i, name in enumerate(MONTH_SHEETS)
}

# Nombres como en el Excel/CSV exportado (origen)
COLS_VENTAS_KEEP = [
    "VENTAS ALMACÉN ANTES IVA",
    "IVA",
    "VENTAS TOTAL ALMACÉN",
    "TOTAL VENTAS DÍA",
    "PELUQUERÍA",
]

# Orden final en interim / SQLite
COLS_VENTAS_OUT = [
    "FECHA",
    "VENTAS_PRE",
    "IVA",
    "VENTAS_POST",
    "TOTAL VENTAS DÍA",
    "PELUQUERÍA",
]
