"""Punto de entrada principal del proyecto ETL.

Ejecuta los pipelines ETL de todas las fuentes de datos y luego
lanza el dashboard web. Si es la primera ejecución (state.json en
null) descarga todos los datos históricos; de lo contrario hace
una actualización incremental del último mes.

Uso (desde el directorio ``etl``, con el intérprete del proyecto)::

    .venv/bin/python main.py           # ETL + dashboard
    .venv/bin/python main.py --etl     # Solo ETL
    .venv/bin/python main.py --dash    # Solo dashboard

Si usas ``uv``: ``uv run python main.py`` (equivale al venv del proyecto).
"""

import argparse
import importlib.util
import sys

from src.etl_monitor import run_etl_with_monitor


def _exit_if_missing_openpyxl() -> None:
    """pandas.read_excel requiere openpyxl; el error por defecto es confuso."""
    if importlib.util.find_spec("openpyxl") is not None:
        return
    print(
        "Falta openpyxl o no usas el entorno del proyecto.\n"
        "  cd etl && uv sync\n"
        "  etl/.venv/bin/python main.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


def run_etl() -> None:
    """Ejecuta ventas, peluquería y Alegra en paralelo con monitor de consola."""
    run_etl_with_monitor()


def parse_args() -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos.

    Returns:
        Namespace con los flags --etl y --dash.
    """
    parser = argparse.ArgumentParser(
        description="ETL Tienda de Mascotas — pipeline + dashboard"
    )
    parser.add_argument(
        "--etl",
        action="store_true",
        help="Ejecutar solo el ETL, sin lanzar el dashboard",
    )
    parser.add_argument(
        "--dash",
        action="store_true",
        help="Lanzar solo el dashboard, sin ejecutar el ETL",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _exit_if_missing_openpyxl()
    args = parse_args()

    print("══════════════════════════════════════")
    print("   ETL Tienda de Mascotas")
    print("══════════════════════════════════════")

    if args.etl:
        # Solo ETL
        run_etl()
    else:
        # Por defecto: ETL + dashboard
        run_etl()
        print("Running dashboard...")
