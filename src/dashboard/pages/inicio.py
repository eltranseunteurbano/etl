"""Resumen ejecutivo global — Tienda + Peluqueria."""

import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

ASISTIO = {"Cliente asistió (default)", "Cliente asistió (Lila)"}
FALTO_AVISO = {"Cliente falta y aviso (verde)"}
FALTO_NO_AVISO = {"Cliente falta y no avisó (amarillo)"}
BONOS = {"Bonos / Regalos a clientes (rosado)"}
CATEGORIAS_CLIENTE = ASISTIO | FALTO_AVISO | FALTO_NO_AVISO | BONOS

MES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

set_browser_tab_title("Dashboard")
st.title("Srta. Eva · Dashboard")
st.caption("Resumen ejecutivo — Tienda + Peluquería")


@st.cache_data
def _load():
    con = sqlite3.connect(DATABASE_PATH)
    df_v = pd.read_sql(
        'SELECT FECHA, VENTAS_POST, "PELUQUERÍA", "TOTAL VENTAS DÍA" '
        "FROM ventas",
        con,
    )
    df_s = pd.read_sql(
        "SELECT FECHA, VALOR, SERVICIO, RAZA FROM peluqueria", con
    )
    df_ap = pd.read_sql(
        "SELECT status FROM alegra_productos", con
    )
    df_c = pd.read_sql(
        "SELECT start, color_label FROM calendar_events", con
    )
    con.close()

    df_v["FECHA"] = pd.to_datetime(df_v["FECHA"], format="mixed")
    df_v["AÑO"] = df_v["FECHA"].dt.year
    df_v["MES"] = df_v["FECHA"].dt.month
    df_v["VENTAS_POST"] = pd.to_numeric(
        df_v["VENTAS_POST"], errors="coerce"
    ).fillna(0)
    df_v["PELUQUERÍA"] = pd.to_numeric(
        df_v["PELUQUERÍA"], errors="coerce"
    ).fillna(0)
    df_v["TOTAL VENTAS DÍA"] = pd.to_numeric(
        df_v["TOTAL VENTAS DÍA"], errors="coerce"
    ).fillna(0)

    df_s["FECHA"] = pd.to_datetime(df_s["FECHA"], format="mixed")
    df_s["AÑO"] = df_s["FECHA"].dt.year
    df_s["MES"] = df_s["FECHA"].dt.month
    df_s["VALOR"] = pd.to_numeric(df_s["VALOR"], errors="coerce").fillna(0)

    df_c["start"] = pd.to_datetime(df_c["start"], errors="coerce")
    df_c["AÑO"] = df_c["start"].dt.year
    df_c["MES"] = df_c["start"].dt.month

    return df_v, df_s, df_ap, df_c


df_v, df_s, df_ap, df_c = _load()

# ── Bloque 1 — KPIs globales ────────────────────────────────────────────────
st.subheader("Ingresos")
total_tienda = df_v["VENTAS_POST"].sum()
total_pelu = df_v["PELUQUERÍA"].sum()
total_combinado = df_v["TOTAL VENTAS DÍA"].sum()
mejor_dia = df_v["TOTAL VENTAS DÍA"].max()

c1, c2 = st.columns(2)
c1.metric("Total tienda", f"${total_tienda:,.0f}")
c2.metric("Total peluquería", f"${total_pelu:,.0f}")
c3, c4 = st.columns(2)
c3.metric("Total combinado", f"${total_combinado:,.0f}")
c4.metric("Mejor día", f"${mejor_dia:,.0f}")

st.subheader("Operación")
dias_con_registro = int((df_v["TOTAL VENTAS DÍA"] > 0).sum())
n_servicios = len(df_s)

df_c_cl = df_c[df_c["color_label"].isin(CATEGORIAS_CLIENTE)]
n_citas = len(df_c_cl)
n_asistio = int(df_c_cl["color_label"].isin(ASISTIO).sum())
n_inasist = n_citas - n_asistio
tasa_asist = n_asistio / n_citas * 100 if n_citas > 0 else 0

c5, c6 = st.columns(2)
c5.metric("Días con registro", f"{dias_con_registro:,}")
c6.metric("Servicios registrados", f"{n_servicios:,}")
c7, c8 = st.columns(2)
c7.metric("Tasa de asistencia", f"{tasa_asist:.1f}%")
c8.metric("Inasistencias", f"{n_inasist:,}")

st.divider()

# ── Bloque 2 — Tendencia mensual combinada ───────────────────────────────────
st.subheader("Tendencia mensual de ingresos")

df_mens = (
    df_v.groupby(["AÑO", "MES"])[["VENTAS_POST", "PELUQUERÍA", "TOTAL VENTAS DÍA"]]
    .sum()
    .reset_index()
)
df_mens["Fecha"] = pd.to_datetime(
    {"year": df_mens["AÑO"], "month": df_mens["MES"], "day": 1}
)
df_mens = df_mens.sort_values("Fecha")

fig_tend = go.Figure()
fig_tend.add_trace(
    go.Bar(
        x=df_mens["Fecha"],
        y=df_mens["VENTAS_POST"],
        name="Tienda",
        marker_color="steelblue",
        yaxis="y1",
    )
)
fig_tend.add_trace(
    go.Bar(
        x=df_mens["Fecha"],
        y=df_mens["PELUQUERÍA"],
        name="Peluquería",
        marker_color="coral",
        yaxis="y1",
    )
)
fig_tend.add_trace(
    go.Scatter(
        x=df_mens["Fecha"],
        y=df_mens["TOTAL VENTAS DÍA"],
        name="Total",
        mode="lines+markers",
        line={"color": "dimgray", "width": 2},
        yaxis="y2",
    )
)
fig_tend.update_layout(
    barmode="group",
    title="Ingresos mensuales: Tienda vs Peluquería",
    xaxis_title="Mes",
    yaxis={"title": "COP"},
    yaxis2={"title": "Total COP", "overlaying": "y", "side": "right"},
    legend={"orientation": "h", "y": -0.15},
    height=460,
)
st.plotly_chart(fig_tend, width="stretch")

st.divider()

# ── Bloque 3 — Composición del revenue ──────────────────────────────────────
st.subheader("Composición del revenue")

col_pie, col_area = st.columns(2)

with col_pie:
    df_pie = pd.DataFrame(
        {
            "Fuente": ["Tienda", "Peluquería"],
            "Total": [total_tienda, total_pelu],
        }
    )
    fig_pie = px.pie(
        df_pie,
        names="Fuente",
        values="Total",
        color="Fuente",
        color_discrete_map={"Tienda": "steelblue", "Peluquería": "coral"},
        title="Participación acumulada",
    )
    st.plotly_chart(fig_pie, width="stretch")

with col_area:
    df_area = df_mens[["Fecha", "VENTAS_POST", "PELUQUERÍA"]].copy()
    df_area = df_area.rename(
        columns={"VENTAS_POST": "Tienda", "PELUQUERÍA": "Peluquería"}
    )
    df_long = df_area.melt(
        id_vars="Fecha", var_name="Fuente", value_name="COP"
    )
    fig_area = px.area(
        df_long,
        x="Fecha",
        y="COP",
        color="Fuente",
        color_discrete_map={"Tienda": "steelblue", "Peluquería": "coral"},
        title="Evolución mensual apilada",
        labels={"COP": "COP", "Fecha": "Mes"},
    )
    fig_area.update_layout(legend={"orientation": "h", "y": -0.2})
    st.plotly_chart(fig_area, width="stretch")

st.divider()

# ── Bloque 4 — Scorecards por módulo ────────────────────────────────────────
st.subheader("Resumen por módulo")

col_t, col_p, col_a = st.columns(3)

# Tienda
with col_t:
    with st.container(border=True):
        st.markdown("**Tienda**")
        df_v_con = df_v[df_v["VENTAS_POST"] > 0]
        mediana_tienda = (
            df_v_con["VENTAS_POST"].median() if len(df_v_con) else 0
        )
        df_mens_t = (
            df_v.groupby(["AÑO", "MES"])["VENTAS_POST"].sum().reset_index()
        )
        mejor_mes_row = (
            df_mens_t.loc[df_mens_t["VENTAS_POST"].idxmax()]
            if len(df_mens_t) else None
        )
        productos_activos = int(
            (df_ap["status"] == "active").sum()
        ) if len(df_ap) else 0
        st.metric("Mediana diaria", f"${mediana_tienda:,.0f}")
        if mejor_mes_row is not None:
            mejor_mes_label = (
                f"{MES_NOMBRES[int(mejor_mes_row['MES'])]} "
                f"{int(mejor_mes_row['AÑO'])}"
            )
            st.metric("Mejor mes", mejor_mes_label)
        st.metric("Productos activos", f"{productos_activos:,}")

# Peluquería
with col_p:
    with st.container(border=True):
        st.markdown("**Peluquería**")
        df_v_pelu = df_v[df_v["PELUQUERÍA"] > 0]
        mediana_pelu = (
            df_v_pelu["PELUQUERÍA"].median() if len(df_v_pelu) else 0
        )
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
        st.metric("Mediana diaria", f"${mediana_pelu:,.0f}")
        st.metric("Servicio más frecuente", str(servicio_top))
        st.metric("Raza más atendida", str(raza_top))

# Agenda
with col_a:
    with st.container(border=True):
        st.markdown("**Agenda**")
        st.metric("Total citas", f"{n_citas:,}")
        st.metric("Tasa de asistencia", f"{tasa_asist:.1f}%")
        # Mes con más inasistencias
        df_inasist = df_c[
            df_c["color_label"].isin(FALTO_AVISO | FALTO_NO_AVISO)
        ]
        if not df_inasist.empty:
            peor = (
                df_inasist.groupby(["AÑO", "MES"])
                .size()
                .reset_index(name="N")
                .sort_values("N", ascending=False)
                .iloc[0]
            )
            peor_label = (
                f"{MES_NOMBRES[int(peor['MES'])]} {int(peor['AÑO'])}"
            )
            st.metric("Mes con más inasistencias", peor_label)
        else:
            st.metric("Mes con más inasistencias", "—")

st.divider()

# ── Bloque 5 — Alertas de tendencia ─────────────────────────────────────────
st.subheader("Tendencia reciente")

for fuente, col in [("Tienda", "VENTAS_POST"), ("Peluquería", "PELUQUERÍA")]:
    ultimos_6 = df_mens.tail(6)
    if len(ultimos_6) >= 6:
        last3 = ultimos_6.tail(3)[col].sum()
        prev3 = ultimos_6.head(3)[col].sum()
        if prev3 > 0:
            delta = (last3 - prev3) / prev3 * 100
            if delta >= 0:
                st.success(
                    f"**{fuente}** — tendencia positiva: "
                    f"ultimos 3 meses (${last3:,.0f}) superaron "
                    f"los 3 anteriores (${prev3:,.0f}) en {delta:.1f}%."
                )
            else:
                st.warning(
                    f"**{fuente}** — tendencia a la baja: "
                    f"ultimos 3 meses (${last3:,.0f}) cayeron "
                    f"{abs(delta):.1f}% frente a los 3 anteriores "
                    f"(${prev3:,.0f})."
                )
