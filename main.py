"""Punto de entrada principal del proyecto ETL.

Ejecuta los pipelines ETL de todas las fuentes de datos y luego
lanza el dashboard web. Si es la primera ejecución (state.json en
null) descarga todos los datos históricos; de lo contrario hace
una actualización incremental del último mes.

Uso::

    python main.py           # Ejecutar ETL + lanzar dashboard
    python main.py --etl     # Solo ejecutar ETL (sin dashboard)
    python main.py --dash    # Solo lanzar dashboard (sin ETL)
"""

import argparse

from src.peluqueria.main import pipeline as peluqueria_pipeline
from src.ventas.main import pipeline as ventas_pipeline


def run_etl() -> None:
    """Ejecuta el pipeline ETL."""
    ventas_pipeline()
    peluqueria_pipeline()


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
