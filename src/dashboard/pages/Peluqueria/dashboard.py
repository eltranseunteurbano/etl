"""Resumen ejecutivo de peluqueria."""

import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

MES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

ASISTIO = {"Cliente asistió (default)", "Cliente asistió (Lila)"}
FALTO_AVISO = {"Cliente falta y aviso (verde)"}
FALTO_NO_AVISO = {"Cliente falta y no avisó (amarillo)"}
BONOS = {"Bonos / Regalos a clientes (rosado)"}
CATEGORIAS_CLIENTE = ASISTIO | FALTO_AVISO | FALTO_NO_AVISO | BONOS

set_browser_tab_title("Peluquería", "Dashboard")
st.title("Peluquería · Resumen")


@st.cache_data
def _load():
    con = sqlite3.connect(DATABASE_PATH)
    df_v = pd.read_sql(
        "SELECT FECHA, \"PELUQUERÍA\" FROM ventas", con
    )
    df_s = pd.read_sql("SELECT * FROM peluqueria", con)
    df_c = pd.read_sql(
        "SELECT start, color_label FROM calendar_events", con
    )
    con.close()
    df_v["FECHA"] = pd.to_datetime(df_v["FECHA"], format="mixed")
    df_v["AÑO"] = df_v["FECHA"].dt.year
    df_v["MES"] = df_v["FECHA"].dt.month
    df_s["FECHA"] = pd.to_datetime(df_s["FECHA"], format="mixed")
    df_s["AÑO"] = df_s["FECHA"].dt.year
    df_s["MES"] = df_s["FECHA"].dt.month
    df_s["VALOR"] = pd.to_numeric(df_s["VALOR"], errors="coerce").fillna(0)
    df_c["start"] = pd.to_datetime(df_c["start"], errors="coerce")
    df_c["AÑO"] = df_c["start"].dt.year
    df_c["MES"] = df_c["start"].dt.month
    return df_v, df_s, df_c


df_v, df_s, df_c = _load()

col_pelu = "PELUQUERÍA"
df_v_con = df_v[df_v[col_pelu] > 0]

# ── Métricas — ingresos ─────────────────────────────────────────────────────
st.subheader("Ingresos de peluquería")
c1, c2 = st.columns(2)
c1.metric("Total acumulado", f"${df_v[col_pelu].sum():,.0f}")
c2.metric(
    "Mediana diaria",
    f"${df_v_con[col_pelu].median():,.0f}" if len(df_v_con) else "—",
)
c3, c4 = st.columns(2)
c3.metric("Mejor día", f"${df_v[col_pelu].max():,.0f}")
c4.metric("Días con registro", f"{len(df_v_con):,}")

st.divider()

# ── Métricas — servicios ────────────────────────────────────────────────────
st.subheader("Servicios registrados")
servicio_top = (
    df_s["SERVICIO"].value_counts().idxmax()
    if not df_s["SERVICIO"].dropna().empty
    else "—"
)
raza_top = (
    df_s["RAZA"].value_counts().idxmax()
    if not df_s["RAZA"].dropna().empty
    else "—"
)
valor_medio = df_s["VALOR"].mean() if len(df_s) else 0

c5, c6 = st.columns(2)
c5.metric("Total servicios", f"{len(df_s):,}")
c6.metric("Servicio más frecuente", str(servicio_top))
c7, c8 = st.columns(2)
c7.metric("Raza más atendida", str(raza_top))
c8.metric("Valor promedio", f"${valor_medio:,.0f}")

st.divider()

# ── Tendencia mensual ───────────────────────────────────────────────────────
st.subheader("Tendencia mensual de ingresos")

df_mens = (
    df_v.groupby(["AÑO", "MES"])[col_pelu]
    .sum()
    .reset_index()
)
df_mens["Fecha"] = pd.to_datetime(
    {"year": df_mens["AÑO"], "month": df_mens["MES"], "day": 1}
)
df_mens = df_mens.sort_values("Fecha")

fig_tend = go.Figure(
    go.Bar(
        x=df_mens["Fecha"],
        y=df_mens[col_pelu],
        name="Ingresos peluquería",
        marker_color="steelblue",
        text=df_mens[col_pelu].apply(lambda v: f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}"),
        textposition="outside",
    )
)
fig_tend.update_layout(
    title="Ingresos mensuales de peluquería",
    xaxis_title="Mes",
    yaxis_title="COP",
    height=440,
)
st.plotly_chart(fig_tend, width="stretch")

# Interpretación 1 — tendencia reciente
ultimos_6 = df_mens.tail(6)
if len(ultimos_6) >= 6:
    last3 = ultimos_6.tail(3)[col_pelu].sum()
    prev3 = ultimos_6.head(3)[col_pelu].sum()
    if prev3 > 0:
        delta = (last3 - prev3) / prev3 * 100
        if delta >= 0:
            st.success(
                f"Tendencia positiva: los ultimos 3 meses "
                f"(\\${last3:,.0f}) superaron los 3 meses anteriores "
                f"(\\${prev3:,.0f}) en un {delta:.1f}%."
            )
        else:
            st.warning(
                f"Tendencia a la baja: los ultimos 3 meses "
                f"(\\${last3:,.0f}) cayeron un {abs(delta):.1f}% frente "
                f"a los 3 meses anteriores (\\${prev3:,.0f})."
            )

st.divider()

# ── Top 5 servicios por revenue ─────────────────────────────────────────────
st.subheader("Top 5 servicios por revenue")

top5_serv = (
    df_s.groupby("SERVICIO")["VALOR"]
    .sum()
    .nlargest(5)
    .reset_index()
)
fig_top5 = px.bar(
    top5_serv,
    x="VALOR",
    y="SERVICIO",
    orientation="h",
    text=top5_serv["VALOR"].apply(lambda v: f"${v:,.0f}"),
    labels={"VALOR": "Revenue total (COP)", "SERVICIO": ""},
    title="Top 5 servicios por revenue acumulado",
)
fig_top5.update_layout(
    yaxis={"categoryorder": "total ascending"},
    height=320,
)
st.plotly_chart(fig_top5, width="stretch")

st.divider()

# ── Resumen de asistencia ───────────────────────────────────────────────────
st.subheader("Asistencia de clientes (Google Calendar)")

df_c_cl = df_c[df_c["color_label"].isin(CATEGORIAS_CLIENTE)].copy()

n_total_cl = len(df_c_cl)
n_asistio = df_c_cl["color_label"].isin(ASISTIO).sum()
n_falto_aviso = df_c_cl["color_label"].isin(FALTO_AVISO).sum()
n_falto_no = df_c_cl["color_label"].isin(FALTO_NO_AVISO).sum()
n_bonos = df_c_cl["color_label"].isin(BONOS).sum()

if n_total_cl > 0:
    df_pie = pd.DataFrame(
        {
            "Categoria": [
                "Asistio",
                "No asistio y aviso",
                "No asistio y no aviso",
                "Bonos y regalos",
            ],
            "Cantidad": [n_asistio, n_falto_aviso, n_falto_no, n_bonos],
        }
    )
    fig_pie = px.pie(
        df_pie,
        names="Categoria",
        values="Cantidad",
        color="Categoria",
        title="Distribucion de eventos de clientes",
        color_discrete_map={
            "Asistio": "mediumseagreen",
            "No asistio y aviso": "darkorange",
            "No asistio y no aviso": "firebrick",
            "Bonos y regalos": "steelblue",
        },
    )
    st.plotly_chart(fig_pie, width="stretch")

    # Interpretación 2 — inasistencias
    n_inasist = n_falto_aviso + n_falto_no
    pct_inasist = n_inasist / n_total_cl * 100
    st.info(
        f"De los {n_total_cl} eventos de clientes registrados, "
        f"{n_inasist} ({pct_inasist:.1f}%) fueron inasistencias. "
        f"De esas, {n_falto_no} no avisaron."
    )
else:
    st.info("No hay datos de asistencia en calendar_events.")
