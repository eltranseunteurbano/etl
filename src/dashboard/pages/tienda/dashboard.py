"""Resumen ejecutivo de la tienda."""

import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

MES_NOMBRES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

set_browser_tab_title("Tienda", "Dashboard")
st.title("Tienda · Resumen")


@st.cache_data
def _load():
    con = sqlite3.connect(DATABASE_PATH)
    df_v = pd.read_sql(
        "SELECT * FROM ventas ORDER BY FECHA", con, parse_dates=["FECHA"]
    )
    df_f = pd.read_sql(
        "SELECT * FROM alegra_facturas ORDER BY date",
        con,
        parse_dates=["date"],
    )
    df_p = pd.read_sql("SELECT * FROM alegra_productos", con)
    con.close()
    df_v["AÑO"] = df_v["FECHA"].dt.year
    df_v["MES"] = df_v["FECHA"].dt.month
    df_f["AÑO"] = df_f["date"].dt.year
    df_f["MES"] = df_f["date"].dt.month
    return df_v, df_f, df_p


df_v, df_f, df_p = _load()
df_activos = df_p[df_p["status"] == "active"].copy()
df_con_ventas = df_p[df_p["total_revenue"] > 0].copy()

# ── Métricas — ventas diarias ───────────────────────────────────────────────
st.subheader("Ventas diarias (libro de ventas)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total acumulado", f"${df_v['VENTAS_POST'].sum():,.0f}")
c2.metric(
    "Mediana diaria", f"${df_v['TOTAL VENTAS DÍA'].median():,.0f}"
)
c3.metric("Mejor día", f"${df_v['TOTAL VENTAS DÍA'].max():,.0f}")
c4.metric("Días registrados", f"{len(df_v):,}")

st.divider()

# ── Métricas — productos y facturas ────────────────────────────────────────
st.subheader("Productos y facturación (Alegra)")
top_prod_name = df_p.loc[df_p["total_revenue"].idxmax(), "name"]
label = (
    str(top_prod_name)[:28] + "…"
    if isinstance(top_prod_name, str) and len(top_prod_name) > 28
    else str(top_prod_name or "")
)
c5, c6, c7, c8 = st.columns(4)
c5.metric("Revenue facturado", f"${df_f['total_product'].sum():,.0f}")
c6.metric("Facturas únicas", f"{df_f['id'].nunique():,}")
c7.metric("Productos con ventas", f"{len(df_con_ventas):,}")
c8.metric("Producto líder", label)

st.divider()

# ── Tendencia mensual unificada ──────────────────────────────────────────────
st.subheader("Tendencia mensual de revenue")

df_mens_v = (
    df_v.groupby(["AÑO", "MES"])["VENTAS_POST"]
    .sum()
    .reset_index()
)
df_mens_v["Fecha"] = pd.to_datetime(
    {"year": df_mens_v["AÑO"], "month": df_mens_v["MES"], "day": 1}
)
df_mens_v = df_mens_v.sort_values("Fecha")

df_mens_f = (
    df_f.groupby(["AÑO", "MES"])["total_product"]
    .sum()
    .reset_index()
)
df_mens_f["Fecha"] = pd.to_datetime(
    {"year": df_mens_f["AÑO"], "month": df_mens_f["MES"], "day": 1}
)
df_mens_f = df_mens_f.sort_values("Fecha")

fig_tend = go.Figure()
fig_tend.add_trace(
    go.Bar(
        x=df_mens_v["Fecha"],
        y=df_mens_v["VENTAS_POST"],
        name="Ventas diarias",
        marker_color="steelblue",
    )
)
fig_tend.add_trace(
    go.Bar(
        x=df_mens_f["Fecha"],
        y=df_mens_f["total_product"],
        name="Revenue productos (Alegra)",
        marker_color="coral",
    )
)
fig_tend.update_layout(
    barmode="group",
    title="Revenue mensual — ventas diarias vs productos facturados",
    xaxis_title="Mes",
    yaxis_title="COP",
    legend={"orientation": "h", "y": -0.15},
    height=480,
)
st.plotly_chart(fig_tend, width="stretch")

# Interpretación 1 — tendencia reciente
ultimos_6 = df_mens_v.tail(6)
if len(ultimos_6) >= 6:
    last3 = ultimos_6.tail(3)["VENTAS_POST"].sum()
    prev3 = ultimos_6.head(3)["VENTAS_POST"].sum()
    if prev3 > 0:
        delta = (last3 - prev3) / prev3 * 100
        if delta >= 0:
            st.success(
                f"Tendencia positiva: las ventas de los ultimos 3 meses "
                f"(\\${last3:,.0f}) superaron los 3 meses anteriores "
                f"(\\${prev3:,.0f}) en un {delta:.1f}%."
            )
        else:
            st.warning(
                f"Tendencia a la baja: las ventas de los ultimos 3 meses "
                f"(\\${last3:,.0f}) cayeron un {abs(delta):.1f}% frente a los "
                f"3 meses anteriores (\\${prev3:,.0f})."
            )

st.divider()

# ── Top 5 productos ──────────────────────────────────────────────────────────
st.subheader("Top 5 productos por revenue")

top5 = df_con_ventas.nlargest(5, "total_revenue")[
    ["name", "total_revenue", "total_sold_quantity"]
].copy()
fig_top5 = px.bar(
    top5,
    x="total_revenue",
    y="name",
    orientation="h",
    text=top5["total_revenue"].apply(lambda v: f"${v:,.0f}"),
    labels={"total_revenue": "Revenue total (COP)", "name": ""},
    title="Top 5 productos por revenue total",
)
fig_top5.update_layout(
    yaxis={"categoryorder": "total ascending"},
    height=360,
)
st.plotly_chart(fig_top5, width="stretch")

st.divider()

# ── Pareto ───────────────────────────────────────────────────────────────────
st.subheader("Concentración de revenue (Pareto)")

df_par = (
    df_con_ventas[["name", "total_revenue"]]
    .sort_values("total_revenue", ascending=False)
    .reset_index(drop=True)
    .copy()
)
df_par["pct_rev"] = (
    df_par["total_revenue"].cumsum() / df_par["total_revenue"].sum() * 100
)
corte_80 = df_par[df_par["pct_rev"] >= 80].iloc[0]
n_prod_80 = int(corte_80.name) + 1
pct_prod_80 = n_prod_80 / len(df_par) * 100

st.info(
    f"De los {len(df_par)} productos con ventas registradas, "
    f"solo los {n_prod_80} mas vendidos ({pct_prod_80:.1f}% del catalogo) "
    f"concentran el 80% del revenue total. "
    f"Los {len(df_par) - n_prod_80} productos restantes generan el 20% restante."
)

st.divider()

# ── Salud del catálogo ───────────────────────────────────────────────────────
st.subheader("Salud del catálogo")

n_sin_venta = len(df_activos[df_activos["total_revenue"] == 0])
n_inact_con = len(
    df_p[(df_p["status"] == "inactive") & (df_p["total_revenue"] > 0)]
)
cs1, cs2 = st.columns(2)
cs1.metric("Activos sin ventas", f"{n_sin_venta:,}")
cs2.metric("Inactivos con ventas", f"{n_inact_con:,}")

# Interpretación 2 — productividad del catálogo
n_activos_con = len(df_activos[df_activos["total_revenue"] > 0])
pct_activos_con = (
    n_activos_con / len(df_activos) * 100 if len(df_activos) > 0 else 0
)
st.caption(
    f"Solo el {pct_activos_con:.1f}% del catalogo activo "
    f"({n_activos_con} de {len(df_activos)} productos) tiene ventas registradas. "
    "El resto puede ser candidato a revision o impulso comercial."
)
