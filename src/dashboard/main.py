import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
_rp = str(_root)
if _rp not in sys.path:
    sys.path.insert(0, _rp)

import streamlit as st  # noqa: E402

main_dashboard = st.Page(
    "pages/inicio.py",
    title="Dashboard",
    icon=":material/home:",
    url_path="dashboard",
    default=True,
)
tienda_dashboard = st.Page(
    "pages/tienda/dashboard.py",
    title="Dashboard",
    icon=":material/store:",
    url_path="tienda_dashboard",
)
tienda_ventas = st.Page(
    "pages/tienda/ventas.py",
    title="Ventas",
    icon=":material/point_of_sale:",
    url_path="tienda_ventas",
)
tienda_productos = st.Page(
    "pages/tienda/productos.py",
    title="Productos",
    icon=":material/inventory_2:",
    url_path="tienda_productos",
)
peluqueria_dashboard = st.Page(
    "pages/peluqueria/dashboard.py",
    title="Dashboard",
    icon=":material/pets:",
    url_path="peluqueria_dashboard",
)
peluqueria_agenda = st.Page(
    "pages/peluqueria/agenda.py",
    title="Agenda",
    icon=":material/calendar_month:",
    url_path="peluqueria_agenda",
)
peluqueria_ventas = st.Page(
    "pages/peluqueria/ventas.py",
    title="Ventas",
    icon=":material/payments:",
    url_path="peluqueria_ventas",
)

nav = st.navigation(
    {
        "": [main_dashboard],
        "Tienda": [
            tienda_dashboard,
            tienda_ventas,
            tienda_productos,
        ],
        "Peluquería": [
            peluqueria_dashboard,
            peluqueria_agenda,
            peluqueria_ventas,
        ],
    }
)
nav.run()
