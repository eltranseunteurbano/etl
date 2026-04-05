"""Analisis de agenda y asistencia de peluqueria."""

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

DIA_NOMBRES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

ASISTIO = {"Cliente asistió (default)", "Cliente asistió (Lila)"}
FALTO_AVISO = {"Cliente falta y aviso (verde)"}
FALTO_NO_AVISO = {"Cliente falta y no avisó (amarillo)"}
BONOS = {"Bonos / Regalos a clientes (rosado)"}
CLIENTES = ASISTIO | FALTO_AVISO | FALTO_NO_AVISO | BONOS


# Etiquetas para mostrar en gráficos
def _label(color_label: str) -> str:
    if color_label in ASISTIO:
        return "Asistio"
    if color_label in FALTO_AVISO:
        return "No asistio y aviso"
    if color_label in FALTO_NO_AVISO:
        return "No asistio y no aviso"
    if color_label in BONOS:
        return "Bonos y regalos"
    return "Otro"


set_browser_tab_title("Peluquería", "Agenda")
st.title("Peluquería · Agenda")


@st.cache_data
def _load():
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql("SELECT * FROM calendar_events", con)
    con.close()
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    df = df.dropna(subset=["start"])
    df["AÑO"] = df["start"].dt.year
    df["MES"] = df["start"].dt.month
    df["DIA_SEMANA"] = df["start"].dt.dayofweek
    df["HORA"] = df["start"].dt.hour
    return df


df = _load()

# ── Métricas rápidas ────────────────────────────────────────────────────────
df_cl = df[df["color_label"].isin(CLIENTES)]
n_total = len(df)
n_clientes = len(df_cl)
n_asistio = df_cl["color_label"].isin(ASISTIO).sum()
n_inasist = n_clientes - n_asistio
pct_asist = n_asistio / n_clientes * 100 if n_clientes > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total eventos", f"{n_total:,}")
c2.metric("Eventos de clientes", f"{n_clientes:,}")
c3.metric("Tasa de asistencia", f"{pct_asist:.1f}%")
c4.metric("Inasistencias", f"{n_inasist:,}")

st.divider()

# ── Pestañas ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(
    [
        "📋 Resumen de eventos",
        "🚫 Inasistencias",
        "📈 Tendencia de asistencia",
    ]
)

# ── Tab 1: Resumen de eventos ────────────────────────────────────────────────
with tab1:
    st.subheader("Distribución por tipo de evento")

    df_cat = df_cl.copy()
    df_cat["Categoria"] = df_cat["color_label"].apply(_label)

    cat_counts = (
        df_cat["Categoria"]
        .value_counts()
        .reset_index()
        .rename(columns={"count": "Cantidad"})
    )
    fig_pie_all = px.pie(
        cat_counts,
        names="Categoria",
        values="Cantidad",
        color="Categoria",
        title="Eventos de clientes por categoria",
        color_discrete_map={
            "Asistio": "mediumseagreen",
            "No asistio y aviso": "darkorange",
            "No asistio y no aviso": "firebrick",
            "Bonos y regalos": "steelblue",
        },
    )
    st.plotly_chart(fig_pie_all, width="stretch")

    st.divider()

    # Tabla resumen con porcentajes
    st.subheader("Tabla resumen por categoría")
    cat_counts["% del total"] = (
        cat_counts["Cantidad"] / cat_counts["Cantidad"].sum() * 100
    ).round(1)
    cat_counts["% del total"] = cat_counts["% del total"].apply(
        lambda v: f"{v:.1f}%"
    )
    st.dataframe(cat_counts, hide_index=True, width="stretch")

    st.divider()

    # Rango de fechas
    st.subheader("Rango de fechas cubierto")
    fecha_min = df["start"].min()
    fecha_max = df["start"].max()
    st.info(
        f"Los eventos cubren desde el {fecha_min.strftime('%d/%m/%Y')} "
        f"hasta el {fecha_max.strftime('%d/%m/%Y')} "
        f"({(fecha_max - fecha_min).days} días)."
    )

# ── Tab 2: Inasistencias ─────────────────────────────────────────────────────
with tab2:
    st.subheader("Inasistencias por mes")

    df_inasist = df[
        df["color_label"].isin(FALTO_AVISO | FALTO_NO_AVISO)
    ].copy()

    if df_inasist.empty:
        st.info("No hay registros de inasistencia en los datos.")
    else:
        df_inasist["Tipo"] = df_inasist["color_label"].apply(
            lambda v: (
                "No asistio y aviso"
                if v in FALTO_AVISO
                else "No asistio y no aviso"
            )
        )
        df_inasist["Mes"] = df_inasist["MES"].map(MES_NOMBRES)

        # Bar apilado mensual
        mens_inasist = (
            df_inasist.groupby(["AÑO", "MES", "Tipo"])
            .size()
            .reset_index(name="Cantidad")
        )
        mens_inasist["Fecha"] = pd.to_datetime(
            {
                "year": mens_inasist["AÑO"],
                "month": mens_inasist["MES"],
                "day": 1,
            }
        )
        mens_inasist = mens_inasist.sort_values("Fecha")

        fig_stack = px.bar(
            mens_inasist,
            x="Fecha",
            y="Cantidad",
            color="Tipo",
            barmode="stack",
            labels={"Fecha": "Mes", "Cantidad": "Inasistencias"},
            title="Inasistencias mensuales por tipo",
            color_discrete_map={
                "No asistio y aviso": "darkorange",
                "No asistio y no aviso": "firebrick",
            },
        )
        st.plotly_chart(fig_stack, width="stretch")

        st.divider()

        # Meses con más inasistencias (top)
        st.subheader("Meses con más inasistencias")
        top_mes_inasist = (
            df_inasist.groupby(["AÑO", "MES"])
            .size()
            .reset_index(name="Total")
            .sort_values("Total", ascending=False)
            .head(10)
        )
        top_mes_inasist["Periodo"] = top_mes_inasist.apply(
            lambda r: f"{MES_NOMBRES[r['MES']]} {r['AÑO']}", axis=1
        )
        fig_top_inasist = px.bar(
            top_mes_inasist,
            x="Total",
            y="Periodo",
            orientation="h",
            text="Total",
            labels={"Total": "Inasistencias", "Periodo": ""},
            title="Top 10 meses con más inasistencias",
            color_discrete_sequence=["coral"],
        )
        fig_top_inasist.update_layout(
            yaxis={"categoryorder": "total ascending"}, height=440
        )
        st.plotly_chart(fig_top_inasist, width="stretch")

        # Interpretación: mes con peor tasa de no-show
        df_cl_mens = (
            df_cl.groupby(["AÑO", "MES"]).size().reset_index(name="Citas")
        )
        df_inasist_mens = (
            df_inasist.groupby(["AÑO", "MES"])
            .size()
            .reset_index(name="Inasist")
        )
        merged = df_cl_mens.merge(
            df_inasist_mens, on=["AÑO", "MES"], how="left"
        ).fillna(0)
        merged["Tasa"] = merged["Inasist"] / merged["Citas"] * 100
        peor = merged.loc[merged["Tasa"].idxmax()]
        st.warning(
            f"El mes con mayor tasa de inasistencia fue "
            f"{MES_NOMBRES[int(peor['MES'])]} {int(peor['AÑO'])}: "
            f"{int(peor['Inasist'])} de {int(peor['Citas'])} citas "
            f"({peor['Tasa']:.1f}%)."
        )

        st.divider()

        # Inasistencias por hora del día
        st.subheader("Inasistencias por hora del día")
        st.caption(
            "Hora de inicio de la cita segun Google Calendar."
        )
        hora_inasist = (
            df_inasist.groupby("HORA")
            .size()
            .reset_index(name="Inasistencias")
        )
        fig_hora = px.bar(
            hora_inasist,
            x="HORA",
            y="Inasistencias",
            text="Inasistencias",
            labels={"HORA": "Hora del día", "Inasistencias": "Inasistencias"},
            title="Inasistencias por hora del día",
            color_discrete_sequence=["firebrick"],
        )
        fig_hora.update_traces(textposition="outside")
        fig_hora.update_layout(xaxis={"dtick": 1})
        st.plotly_chart(fig_hora, width="stretch")
        if len(hora_inasist) > 0:
            hora_peor = hora_inasist.loc[
                hora_inasist["Inasistencias"].idxmax(), "HORA"
            ]
            st.caption(
                f"La hora con mas inasistencias es las {hora_peor}:00 hrs."
            )

        st.divider()

        # Inasistencias por día de semana
        st.subheader("Inasistencias por día de la semana")
        dia_inasist = (
            df_inasist.groupby(["DIA_SEMANA", "Tipo"])
            .size()
            .reset_index(name="Cantidad")
        )
        dia_inasist["Día"] = dia_inasist["DIA_SEMANA"].map(DIA_NOMBRES)
        fig_dia_in = px.bar(
            dia_inasist.sort_values("DIA_SEMANA"),
            x="Día",
            y="Cantidad",
            color="Tipo",
            barmode="stack",
            category_orders={"Día": list(DIA_NOMBRES.values())},
            color_discrete_map={
                "No asistio y aviso": "darkorange",
                "No asistio y no aviso": "firebrick",
            },
            labels={"Cantidad": "Inasistencias", "Día": ""},
            title="Inasistencias por día de la semana",
        )
        st.plotly_chart(fig_dia_in, width="stretch")

# ── Tab 3: Tendencia de asistencia ───────────────────────────────────────────
with tab3:
    st.subheader("Tasa de asistencia mensual")

    df_cl_m = df_cl.groupby(["AÑO", "MES"]).size().reset_index(name="Citas")
    df_asist_m = (
        df_cl[df_cl["color_label"].isin(ASISTIO)]
        .groupby(["AÑO", "MES"])
        .size()
        .reset_index(name="Asistencias")
    )
    df_tend = df_cl_m.merge(df_asist_m, on=["AÑO", "MES"], how="left").fillna(
        0
    )
    df_tend["Fecha"] = pd.to_datetime(
        {"year": df_tend["AÑO"], "month": df_tend["MES"], "day": 1}
    )
    df_tend = df_tend.sort_values("Fecha")
    df_tend["Tasa_pct"] = df_tend["Asistencias"] / df_tend["Citas"] * 100

    fig_tend = go.Figure()
    fig_tend.add_trace(
        go.Bar(
            x=df_tend["Fecha"],
            y=df_tend["Asistencias"],
            name="Asistencias",
            marker_color="steelblue",
            yaxis="y1",
        )
    )
    fig_tend.add_trace(
        go.Scatter(
            x=df_tend["Fecha"],
            y=df_tend["Tasa_pct"],
            name="Tasa de asistencia %",
            mode="lines+markers",
            line={"color": "coral", "width": 2},
            yaxis="y2",
        )
    )
    fig_tend.update_layout(
        title="Asistencias y tasa mensual",
        xaxis_title="Mes",
        yaxis={"title": "Asistencias"},
        yaxis2={
            "title": "Tasa (%)",
            "overlaying": "y",
            "side": "right",
            "range": [0, 110],
        },
        legend={"orientation": "h", "y": -0.15},
        height=480,
    )
    st.plotly_chart(fig_tend, width="stretch")

    st.divider()

    # Distribución de eventos por día de semana
    st.subheader("Distribución de citas por día de la semana")
    df_cl_dia = df_cl.copy()
    df_cl_dia["Día"] = df_cl_dia["DIA_SEMANA"].map(DIA_NOMBRES)
    df_cl_dia["Categoria"] = df_cl_dia["color_label"].apply(_label)

    dia_counts = (
        df_cl_dia.groupby(["Día", "DIA_SEMANA", "Categoria"])
        .size()
        .reset_index(name="Cantidad")
    )
    fig_dia = px.bar(
        dia_counts.sort_values("DIA_SEMANA"),
        x="Día",
        y="Cantidad",
        color="Categoria",
        barmode="stack",
        category_orders={"Día": list(DIA_NOMBRES.values())},
        color_discrete_map={
            "Asistio": "mediumseagreen",
            "No asistio y aviso": "darkorange",
            "No asistio y no aviso": "firebrick",
            "Bonos y regalos": "steelblue",
        },
        title="Citas por día de la semana",
        labels={"Cantidad": "Citas", "Día": ""},
    )
    st.plotly_chart(fig_dia, width="stretch")

    st.divider()

    # Heatmap día × hora de inasistencias
    st.subheader("Patron de inasistencias: día × hora")
    st.caption(
        "Concentracion de inasistencias por combinacion de dia de semana "
        "y hora de la cita. Colores mas intensos = mas ausencias."
    )
    df_inasist_all = df[
        df["color_label"].isin(FALTO_AVISO | FALTO_NO_AVISO)
    ].copy()
    if not df_inasist_all.empty:
        heat_abs = (
            df_inasist_all.groupby(["DIA_SEMANA", "HORA"])
            .size()
            .reset_index(name="Inasistencias")
        )
        heat_pivot = (
            heat_abs.pivot(
                index="DIA_SEMANA", columns="HORA", values="Inasistencias"
            )
            .fillna(0)
            .astype(int)
        )
        heat_pivot.index = [DIA_NOMBRES[i] for i in heat_pivot.index]
        fig_heat = px.imshow(
            heat_pivot,
            text_auto=True,
            color_continuous_scale="Reds",
            labels={"x": "Hora", "y": "Día", "color": "Inasistencias"},
            title="Heatmap de inasistencias por día y hora",
            aspect="auto",
        )
        fig_heat.update_layout(height=350)
        st.plotly_chart(fig_heat, width="stretch")
    else:
        st.info("Sin datos de inasistencia para mostrar el heatmap.")
