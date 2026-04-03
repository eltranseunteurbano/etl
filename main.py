"""Punto de entrada principal del proyecto ETL.

Ejecuta los pipelines ETL de todas las fuentes de datos y luego
lanza el dashboard web. Si es la primera ejecución (state.json en
null) descarga todos los datos históricos; de lo contrario hace
una actualización incremental del último mes.

Uso (desde el directorio ``etl``, con el intérprete del proyecto)::

    .venv/bin/python main.py           # ETL + dashboard
    .venv/bin/python main.py --etl     # Solo ETL
    .venv/bin/python main.py --dash    # Solo dashboard

Si usas ``uv``: ``uv run python main.py --dash`` lanza solo Streamlit, etc.
"""

import argparse
import importlib.util
import logging
import subprocess
import sys
from pathlib import Path

from src.config.settings import setup_logging
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
    """Ejecuta todos los pipelines ETL en paralelo con monitor de consola."""
    try:
        run_etl_with_monitor()
    except Exception as exc:
        logging.getLogger("etl").critical(
            "ETL terminó con errores: %s", exc, exc_info=True
        )
        raise SystemExit(1) from exc


def run_dashboard() -> None:
    """Arranca el dashboard con Streamlit (requiere ``streamlit run``)."""
    script = Path(__file__).resolve().parent / "src" / "dashboard" / "main.py"
    if not script.is_file():
        print(
            f"No se encontró el entrypoint del dashboard: {script}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(script)],
        check=False,
    )
    raise SystemExit(result.returncode)


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
    setup_logging()
    args = parse_args()

    if args.etl and args.dash:
        print(
            "No uses --etl y --dash a la vez; elige uno.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if not args.dash:
        _exit_if_missing_openpyxl()

    print("══════════════════════════════════════")
    print("   ETL Tienda de Mascotas")
    print("══════════════════════════════════════")

    if args.dash:
        run_dashboard()
    elif args.etl:
        run_etl()
    else:
        run_etl()
        run_dashboard()
