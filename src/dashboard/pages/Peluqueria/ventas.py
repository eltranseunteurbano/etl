"""Analisis de ingresos de peluqueria."""

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

set_browser_tab_title("Peluquería", "Ventas")
st.title("Peluquería · Ventas")

COL_PELU = "PELUQUERÍA"


@st.cache_data
def _load_ventas() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql(f'SELECT FECHA, "{COL_PELU}" FROM ventas', con)
    con.close()
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="mixed")
    df["AÑO"] = df["FECHA"].dt.year
    df["MES"] = df["FECHA"].dt.month
    df["DIA_SEMANA"] = df["FECHA"].dt.dayofweek
    return df


@st.cache_data
def _load_servicios() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql("SELECT * FROM peluqueria", con)
    con.close()
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="mixed")
    df["AÑO"] = df["FECHA"].dt.year
    df["MES"] = df["FECHA"].dt.month
    # VALOR a numérico por si viene como string
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce").fillna(0)
    df["PESO"] = pd.to_numeric(df["PESO"], errors="coerce")
    return df


df = _load_ventas()
df_s = _load_servicios()

# Solo días con actividad de peluquería
df_act = df[df[COL_PELU] > 0].copy()

# ── Métricas rápidas ────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
c1.metric("Días con registro", f"{len(df_act):,}")
c2.metric("Mediana diaria", f"${df_act[COL_PELU].median():,.0f}")
c3, c4 = st.columns(2)
c3.metric("Mejor día", f"${df_act[COL_PELU].max():,.0f}")
c4.metric("Total servicios registrados", f"{len(df_s):,}")

st.divider()

# ── Pestañas ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📊 Estadísticos",
        "📈 Distribución",
        "📅 Por año",
        "✂ Análisis de servicios",
        "🗓 Servicios por día",
        "👥 Clientes",
    ]
)

# ── Tab 1: Estadísticos ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Estadísticos descriptivos — Peluquería diaria")

    desc = df_act[COL_PELU].describe()
    stats = {
        "Registros": int(desc["count"]),
        "Promedio": desc["mean"],
        "Mediana": desc["50%"],
        "Desviación estándar": desc["std"],
        "Mínimo": desc["min"],
        "Percentil 25%": desc["25%"],
        "Percentil 75%": desc["75%"],
        "Máximo": desc["max"],
        "Asimetría (skewness)": df_act[COL_PELU].skew(),
        "Curtosis (kurtosis)": df_act[COL_PELU].kurt(),
    }

    fmt = {}
    for k, v in stats.items():
        if k == "Registros":
            fmt[k] = f"{v:,}"
        elif k in ("Asimetría (skewness)", "Curtosis (kurtosis)"):
            fmt[k] = f"{v:.4f}"
        else:
            fmt[k] = f"${v:,.0f}"

    st.dataframe(
        pd.DataFrame({"Estadístico": list(fmt.keys()), "Valor": list(fmt.values())}),
        hide_index=True,
        width="stretch",
    )

    st.divider()
    st.subheader("Días destacados")

    def _fmt_dias(sub: pd.DataFrame) -> pd.DataFrame:
        out = sub[["FECHA", COL_PELU]].copy()
        out["Día"] = sub["DIA_SEMANA"].map(DIA_NOMBRES)
        out["Mes"] = sub["MES"].map(MES_NOMBRES)
        out["Fecha"] = out["FECHA"].dt.strftime("%d/%m/%Y")
        out["Total"] = out[COL_PELU].apply(lambda v: f"${v:,.0f}")
        return out[["Fecha", "Día", "Mes", "Total"]]

    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Top 10 días con mayores ingresos**")
        st.dataframe(
            _fmt_dias(df_act.nlargest(10, COL_PELU)),
            hide_index=True,
            width="stretch",
        )
    with cb:
        st.markdown("**Top 10 días con menores ingresos**")
        st.dataframe(
            _fmt_dias(df_act.nsmallest(10, COL_PELU)),
            hide_index=True,
            width="stretch",
        )

# ── Tab 2: Distribución ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Distribución de ingresos diarios")

    p99 = df_act[COL_PELU].quantile(0.99)
    outliers = df_act[df_act[COL_PELU] > p99]
    n_out = len(outliers)

    fig_hist = px.histogram(
        df_act[df_act[COL_PELU] <= p99],
        x=COL_PELU,
        marginal="rug",
        labels={COL_PELU: "Ingresos peluquería día (COP)"},
        title="Distribución de ingresos diarios",
    )
    fig_hist.update_layout(bargap=0.05)
    st.plotly_chart(fig_hist, width="stretch")

    if n_out > 0:
        st.caption(
            f"{n_out} días con ingresos > ${p99:,.0f} (percentil 99) "
            "no se muestran en el histograma."
        )

    fig_box_yr = px.box(
        df_act,
        x="AÑO",
        y=COL_PELU,
        labels={COL_PELU: "Ingresos (COP)", "AÑO": "Año"},
        title="Distribución por año",
    )
    st.plotly_chart(fig_box_yr, width="stretch")

    df_mes_box = df_act.copy()
    df_mes_box["Mes"] = df_mes_box["MES"].map(MES_NOMBRES)
    fig_box_mes = px.box(
        df_mes_box,
        x="Mes",
        y=COL_PELU,
        category_orders={"Mes": list(MES_NOMBRES.values())},
        labels={COL_PELU: "Ingresos (COP)", "Mes": ""},
        title="Distribución por mes",
    )
    st.plotly_chart(fig_box_mes, width="stretch")

    df_dia_box = df_act.copy()
    df_dia_box["Día"] = df_dia_box["DIA_SEMANA"].map(DIA_NOMBRES)
    fig_box_dia = px.box(
        df_dia_box,
        x="Día",
        y=COL_PELU,
        category_orders={"Día": list(DIA_NOMBRES.values())},
        labels={COL_PELU: "Ingresos (COP)", "Día": ""},
        title="Distribución por día de la semana",
    )
    st.plotly_chart(fig_box_dia, width="stretch")

# ── Tab 3: Por año/mes ──────────────────────────────────────────────────────
with tab3:
    years = sorted(df_act["AÑO"].unique())

    st.subheader("Meses ordenados por mediana de ingresos")
    for year in years:
        df_yr = df_act[df_act["AÑO"] == year].copy()
        res_mes = (
            df_yr.groupby("MES")[COL_PELU]
            .agg(["median", "sum", "count"])
            .reset_index()
            .rename(columns={"median": "Mediana", "sum": "Total", "count": "Días"})
            .sort_values("Mediana", ascending=False)
        )
        res_mes["Mes"] = res_mes["MES"].map(MES_NOMBRES)
        with st.expander(f"**{year}**", expanded=True):
            fig_mes = px.bar(
                res_mes,
                x="Mediana",
                y="Mes",
                orientation="h",
                text=res_mes["Mediana"].apply(lambda v: f"${v:,.0f}"),
                labels={"Mediana": "Mediana ingresos día (COP)", "Mes": ""},
                title=f"Mediana diaria por mes — {year}",
            )
            fig_mes.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_mes, width="stretch")
            tabla = res_mes[["Mes", "Mediana", "Total", "Días"]].copy()
            tabla["Mediana"] = tabla["Mediana"].apply(lambda v: f"${v:,.0f}")
            tabla["Total"] = tabla["Total"].apply(lambda v: f"${v:,.0f}")
            st.dataframe(tabla, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Días de la semana ordenados por mediana")
    for year in years:
        df_yr = df_act[df_act["AÑO"] == year].copy()
        res_dia = (
            df_yr.groupby("DIA_SEMANA")[COL_PELU]
            .agg(["median", "count"])
            .reset_index()
            .rename(columns={"median": "Mediana", "count": "Días"})
            .sort_values("Mediana", ascending=False)
        )
        res_dia["Día"] = res_dia["DIA_SEMANA"].map(DIA_NOMBRES)
        with st.expander(f"**{year}**", expanded=True):
            fig_dia = px.bar(
                res_dia,
                x="Mediana",
                y="Día",
                orientation="h",
                text=res_dia["Mediana"].apply(lambda v: f"${v:,.0f}"),
                labels={"Mediana": "Mediana ingresos día (COP)", "Día": ""},
                title=f"Mediana diaria por día de semana — {year}",
            )
            fig_dia.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_dia, width="stretch")
            tabla_dia = res_dia[["Día", "Mediana", "Días"]].copy()
            tabla_dia["Mediana"] = tabla_dia["Mediana"].apply(lambda v: f"${v:,.0f}")
            st.dataframe(tabla_dia, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Meses con más días atípicos por año")
    st.caption(
        "Un día es atípico si su ingreso está fuera de Q1 − 1.5×IQR o Q3 + 1.5×IQR."
    )
    for year in years:
        df_yr = df_act[df_act["AÑO"] == year].copy()
        q1 = df_yr[COL_PELU].quantile(0.25)
        q3 = df_yr[COL_PELU].quantile(0.75)
        iqr = q3 - q1
        df_out = df_yr[
            (df_yr[COL_PELU] < q1 - 1.5 * iqr) | (df_yr[COL_PELU] > q3 + 1.5 * iqr)
        ].copy()
        df_out["Tipo"] = df_out[COL_PELU].apply(
            lambda v: "Alto" if v > q3 + 1.5 * iqr else "Bajo"
        )
        conteo = (
            df_out.groupby("MES")
            .agg(
                Atipicos=("MES", "count"),
                Altos=("Tipo", lambda x: (x == "Alto").sum()),
                Bajos=("Tipo", lambda x: (x == "Bajo").sum()),
            )
            .reset_index()
            .sort_values("Atipicos", ascending=False)
        )
        conteo["Mes"] = conteo["MES"].map(MES_NOMBRES)
        with st.expander(
            f"**{year}** — {len(df_out)} días atípicos en total", expanded=True
        ):
            if conteo.empty:
                st.info("Sin días atípicos este año.")
            else:
                fig_out = px.bar(
                    conteo,
                    x="Mes",
                    y="Atipicos",
                    text="Atipicos",
                    labels={"Atipicos": "Días atípicos", "Mes": ""},
                    title=f"Días atípicos por mes — {year}",
                    color_discrete_sequence=["coral"],
                    category_orders={
                        "Mes": [MES_NOMBRES[m] for m in sorted(conteo["MES"])]
                    },
                )
                st.plotly_chart(fig_out, width="stretch")
                st.dataframe(
                    conteo[["Mes", "Atipicos", "Altos", "Bajos"]],
                    hide_index=True,
                    width="stretch",
                )

# ── Tab 4: Análisis de servicios ─────────────────────────────────────────────
with tab4:
    # Revenue por tipo de servicio
    st.subheader("Revenue por tipo de servicio")
    serv_agg = (
        df_s.groupby("SERVICIO")["VALOR"]
        .agg(Revenue="sum", Cantidad="count", Promedio="mean")
        .reset_index()
        .sort_values("Revenue", ascending=False)
    )
    fig_serv = px.bar(
        serv_agg,
        x="Revenue",
        y="SERVICIO",
        orientation="h",
        text=serv_agg["Revenue"].apply(lambda v: f"${v:,.0f}"),
        labels={"Revenue": "Revenue total (COP)", "SERVICIO": ""},
        title="Revenue acumulado por tipo de servicio",
    )
    fig_serv.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
    st.plotly_chart(fig_serv, width="stretch")

    tabla_serv = serv_agg.copy()
    tabla_serv["Revenue"] = tabla_serv["Revenue"].apply(lambda v: f"${v:,.0f}")
    tabla_serv["Promedio"] = tabla_serv["Promedio"].apply(lambda v: f"${v:,.0f}")
    tabla_serv.columns = ["Servicio", "Revenue", "Cantidad", "Precio promedio"]
    st.dataframe(tabla_serv, hide_index=True, width="stretch")

    st.divider()

    # Razas — tabla visitas y revenue
    st.subheader("Razas: visitas y revenue")
    raza_agg = (
        df_s.groupby("RAZA")["VALOR"]
        .agg(Visitas="count", Revenue="sum")
        .reset_index()
        .sort_values("Revenue", ascending=False)
        .dropna(subset=["RAZA"])
        .reset_index(drop=True)
    )
    tabla_raza = raza_agg.copy()
    tabla_raza["Revenue"] = tabla_raza["Revenue"].apply(lambda v: f"${v:,.0f}")
    tabla_raza.columns = ["Raza", "Visitas", "Revenue"]
    st.dataframe(tabla_raza, hide_index=True, width="stretch")

    st.divider()

    # Pelo — tabla visitas y revenue
    st.subheader("Tipo de pelo: visitas y revenue")
    pelo_agg = (
        df_s.groupby("PELO")["VALOR"]
        .agg(Visitas="count", Revenue="sum")
        .reset_index()
        .sort_values("Revenue", ascending=False)
        .dropna(subset=["PELO"])
        .reset_index(drop=True)
    )
    tabla_pelo = pelo_agg.copy()
    tabla_pelo["Revenue"] = tabla_pelo["Revenue"].apply(lambda v: f"${v:,.0f}")
    tabla_pelo.columns = ["Pelo", "Visitas", "Revenue"]
    st.dataframe(tabla_pelo, hide_index=True, width="stretch")

    st.divider()

    # Distribución de peso
    st.subheader("Distribución de peso de mascotas atendidas")
    peso_valido = df_s["PESO"].dropna()
    if len(peso_valido) > 0:
        p99_peso = peso_valido.quantile(0.99)
        fig_peso = px.histogram(
            peso_valido[peso_valido <= p99_peso],
            nbins=30,
            labels={"value": "Peso (kg)"},
            title="Distribución de peso (excluyendo outliers p99)",
        )
        fig_peso.update_layout(bargap=0.05)
        st.plotly_chart(fig_peso, width="stretch")
        n_out_peso = (peso_valido > p99_peso).sum()
        if n_out_peso > 0:
            st.caption(
                f"{n_out_peso} mascotas con peso > {p99_peso:.1f} kg "
                "(percentil 99) no se muestran."
            )

    st.divider()

    # Top 15 mascotas más visitantes
    st.subheader("Top 15 mascotas con más visitas")
    masc_vis = (
        df_s.groupby("MASCOTA")
        .agg(Visitas=("VALOR", "count"), Revenue=("VALOR", "sum"))
        .reset_index()
        .nlargest(15, "Visitas")
        .dropna(subset=["MASCOTA"])
        .reset_index(drop=True)
    )
    tabla_masc = masc_vis.copy()
    tabla_masc["Revenue"] = tabla_masc["Revenue"].apply(lambda v: f"${v:,.0f}")
    tabla_masc.columns = ["Mascota", "Visitas", "Total gastado"]
    st.dataframe(tabla_masc, hide_index=True, width="stretch")

    st.divider()

    # Peso vs ingresos (scatter)
    st.subheader("Peso de la mascota vs valor del servicio")
    st.caption(
        "Cada punto es un servicio. Permite ver si mascotas más pesadas "
        "generan un ticket mayor."
    )
    df_pw = df_s[df_s["PESO"].notna() & (df_s["PESO"] > 0)].copy()
    if len(df_pw) > 0:
        fig_pw = px.scatter(
            df_pw,
            x="PESO",
            y="VALOR",
            color="SERVICIO",
            hover_data=["RAZA", "MASCOTA"],
            labels={"PESO": "Peso (kg)", "VALOR": "Valor del servicio (COP)"},
            title="Peso vs valor del servicio",
            opacity=0.6,
        )
        st.plotly_chart(fig_pw, width="stretch")

    st.divider()

    # Heatmap raza × servicio
    st.subheader("Raza × servicio (visitas)")
    st.caption("Que servicios demanda cada raza. Solo razas con mas de 2 registros.")
    razas_freq = df_s["RAZA"].value_counts()
    razas_validas = razas_freq[razas_freq > 2].index
    df_rs = df_s[df_s["RAZA"].isin(razas_validas)].copy()
    heat_rs = df_rs.groupby(["RAZA", "SERVICIO"]).size().reset_index(name="Visitas")
    pivot_rs = (
        heat_rs.pivot(index="RAZA", columns="SERVICIO", values="Visitas")
        .fillna(0)
        .astype(int)
    )
    fig_rs = px.imshow(
        pivot_rs,
        text_auto=True,
        color_continuous_scale="Blues",
        labels={"x": "Servicio", "y": "Raza", "color": "Visitas"},
        title="Visitas por raza y tipo de servicio",
        aspect="auto",
    )
    fig_rs.update_layout(height=max(400, len(pivot_rs) * 28))
    st.plotly_chart(fig_rs, width="stretch")


# ── Tab 5: Tendencia y demanda ───────────────────────────────────────────────
with tab5:
    df_s5 = df_s.copy()
    df_s5["DIA_SEMANA"] = df_s5["FECHA"].dt.dayofweek
    df_s5["Día"] = df_s5["DIA_SEMANA"].map(DIA_NOMBRES)

    # Evolución mensual de servicios + ticket promedio
    st.subheader("Evolución mensual de servicios y ticket promedio")
    df_mens_s = (
        df_s.groupby(["AÑO", "MES"])
        .agg(
            Servicios=("VALOR", "count"),
            Revenue=("VALOR", "sum"),
            Ticket=("VALOR", "mean"),
        )
        .reset_index()
    )
    df_mens_s["Fecha"] = pd.to_datetime(
        {"year": df_mens_s["AÑO"], "month": df_mens_s["MES"], "day": 1}
    )
    df_mens_s = df_mens_s.sort_values("Fecha")

    fig_evol = go.Figure()
    fig_evol.add_trace(
        go.Bar(
            x=df_mens_s["Fecha"],
            y=df_mens_s["Servicios"],
            name="Servicios",
            marker_color="steelblue",
            yaxis="y1",
        )
    )
    fig_evol.add_trace(
        go.Scatter(
            x=df_mens_s["Fecha"],
            y=df_mens_s["Ticket"],
            name="Ticket promedio (COP)",
            mode="lines+markers",
            line={"color": "coral", "width": 2},
            yaxis="y2",
        )
    )
    fig_evol.update_layout(
        title="Servicios mensuales y ticket promedio",
        xaxis_title="Mes",
        yaxis={"title": "Servicios"},
        yaxis2={"title": "Ticket promedio (COP)", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": -0.15},
        height=460,
    )
    st.plotly_chart(fig_evol, width="stretch")

    st.divider()
    st.subheader("Visitas y revenue por día de la semana")

    dia_agg = (
        df_s5.groupby(["DIA_SEMANA", "Día"])
        .agg(Visitas=("VALOR", "count"), Revenue=("VALOR", "sum"))
        .reset_index()
        .sort_values("DIA_SEMANA")
    )

    col_v, col_r = st.columns(2)
    with col_v:
        fig_dv = px.bar(
            dia_agg,
            x="Día",
            y="Visitas",
            text="Visitas",
            category_orders={"Día": list(DIA_NOMBRES.values())},
            labels={"Visitas": "Servicios realizados", "Día": ""},
            title="Visitas por día de la semana",
            color_discrete_sequence=["steelblue"],
        )
        fig_dv.update_traces(textposition="outside")
        st.plotly_chart(fig_dv, width="stretch")

    with col_r:
        fig_dr = px.bar(
            dia_agg,
            x="Día",
            y="Revenue",
            text=dia_agg["Revenue"].apply(lambda v: f"${v / 1e6:.1f}M"),
            category_orders={"Día": list(DIA_NOMBRES.values())},
            labels={"Revenue": "Revenue total (COP)", "Día": ""},
            title="Revenue por día de la semana",
            color_discrete_sequence=["coral"],
        )
        fig_dr.update_traces(textposition="outside")
        st.plotly_chart(fig_dr, width="stretch")

    st.divider()

    # Heatmap servicio × día
    st.subheader("Demanda de servicios por día de la semana")
    st.caption("Número de servicios realizados por combinación de tipo y día.")
    heat = df_s5.groupby(["SERVICIO", "DIA_SEMANA"]).size().reset_index(name="Visitas")
    heat_pivot = (
        heat.pivot(index="SERVICIO", columns="DIA_SEMANA", values="Visitas")
        .fillna(0)
        .astype(int)
    )
    heat_pivot.columns = [DIA_NOMBRES[int(c)] for c in heat_pivot.columns]

    fig_heat = px.imshow(
        heat_pivot,
        text_auto=True,
        color_continuous_scale="Blues",
        labels={"x": "Día", "y": "Servicio", "color": "Visitas"},
        title="Heatmap de servicios por día",
        aspect="auto",
    )
    fig_heat.update_layout(height=max(300, len(heat_pivot) * 50))
    st.plotly_chart(fig_heat, width="stretch")

# ── Tab 6: Clientes ──────────────────────────────────────────────────────────
with tab6:
    col_prop = "MASCOTA"

    # ── Nuevas mascotas por mes ──────────────────────────────────────────────
    st.subheader("Nuevas mascotas por mes")
    st.caption("Una mascota es 'nueva' el mes de su primera visita registrada.")
    primera_visita = (
        df_s.dropna(subset=[col_prop]).groupby(col_prop)["FECHA"].min().reset_index()
    )
    primera_visita["AÑO"] = primera_visita["FECHA"].dt.year
    primera_visita["MES"] = primera_visita["FECHA"].dt.month
    nuevos_mes = (
        primera_visita.groupby(["AÑO", "MES"]).size().reset_index(name="Nuevos")
    )
    nuevos_mes["Fecha"] = pd.to_datetime(
        {"year": nuevos_mes["AÑO"], "month": nuevos_mes["MES"], "day": 1}
    )
    nuevos_mes = nuevos_mes.sort_values("Fecha")
    fig_nuevos = px.bar(
        nuevos_mes,
        x="Fecha",
        y="Nuevos",
        text="Nuevos",
        labels={"Fecha": "Mes", "Nuevos": "Clientes nuevos"},
        title="Clientes nuevos por mes",
        color_discrete_sequence=["mediumseagreen"],
    )
    fig_nuevos.update_traces(textposition="outside")
    fig_nuevos.update_layout(height=400)
    st.plotly_chart(fig_nuevos, width="stretch")

    st.divider()

    # ── Segmentación por frecuencia ──────────────────────────────────────────
    st.subheader("Segmentacion de mascotas por frecuencia de visitas")
    freq_cl = df_s.dropna(subset=[col_prop]).groupby(col_prop).size()
    bins = pd.cut(
        freq_cl,
        bins=[0, 1, 5, 10, float("inf")],
        labels=["1 visita", "2-5 visitas", "6-10 visitas", "11+ visitas"],
    )
    seg_counts = bins.value_counts().reset_index()
    seg_counts.columns = ["Segmento", "Clientes"]
    seg_counts = seg_counts.sort_values("Segmento")

    fig_seg = px.pie(
        seg_counts,
        names="Segmento",
        values="Clientes",
        color="Segmento",
        title="Distribucion de clientes por frecuencia",
        color_discrete_map={
            "1 visita": "lightgray",
            "2-5 visitas": "steelblue",
            "6-10 visitas": "coral",
            "11+ visitas": "mediumseagreen",
        },
    )
    st.plotly_chart(fig_seg, width="stretch")
    n_leales = int(freq_cl[freq_cl > 5].count())
    pct_leales = n_leales / len(freq_cl) * 100 if len(freq_cl) > 0 else 0
    st.caption(f"{n_leales} mascotas ({pct_leales:.1f}%) han visitado mas de 5 veces.")

    st.divider()

    # ── Pareto de mascotas ───────────────────────────────────────────────────
    st.subheader("Concentracion de revenue por mascota (Pareto)")
    rev_cl = (
        df_s.dropna(subset=[col_prop])
        .groupby(col_prop)["VALOR"]
        .sum()
        .sort_values(ascending=False)
        .reset_index(drop=True)
    )
    rev_df = pd.DataFrame(
        {
            "pct_clientes": (rev_cl.index + 1) / len(rev_cl) * 100,
            "pct_revenue": rev_cl.cumsum() / rev_cl.sum() * 100,
        }
    )
    corte = rev_df[rev_df["pct_revenue"] >= 80].iloc[0]
    pct_cl_80 = corte["pct_clientes"]
    n_cl_80 = int(round(pct_cl_80 / 100 * len(rev_cl)))

    fig_pareto = go.Figure()
    fig_pareto.add_trace(
        go.Scatter(
            x=rev_df["pct_clientes"],
            y=rev_df["pct_revenue"],
            mode="lines",
            name="Revenue acumulado",
            line={"color": "steelblue", "width": 2},
        )
    )
    fig_pareto.add_hline(
        y=80,
        line_dash="dash",
        line_color="firebrick",
        annotation_text="80%",
        annotation_position="left",
    )
    fig_pareto.add_vline(
        x=pct_cl_80,
        line_dash="dash",
        line_color="coral",
        annotation_text=f"{pct_cl_80:.1f}% clientes",
        annotation_position="top right",
    )
    fig_pareto.update_layout(
        xaxis_title="% de clientes (mayor a menor revenue)",
        yaxis_title="% revenue acumulado",
        height=400,
    )
    st.plotly_chart(fig_pareto, width="stretch")
    st.info(
        f"El {pct_cl_80:.1f}% de las mascotas ({n_cl_80} de {len(rev_cl)}) "
        f"genera el 80% del revenue total."
    )

    st.divider()

    # ── Retencion año a año ──────────────────────────────────────────────────
    st.subheader("Retencion de mascotas año a año")
    st.caption("Porcentaje de mascotas atendidas en un año que volvieron el siguiente.")
    years = sorted(df_s["AÑO"].unique())
    retention = []
    for i in range(len(years) - 1):
        y1, y2 = years[i], years[i + 1]
        cl_y1 = set(df_s[df_s["AÑO"] == y1][col_prop].dropna())
        cl_y2 = set(df_s[df_s["AÑO"] == y2][col_prop].dropna())
        retenidos = len(cl_y1 & cl_y2)
        total = len(cl_y1)
        retention.append(
            {
                "Periodo": f"{y1} → {y2}",
                "Mascotas año anterior": total,
                "Regresaron": retenidos,
                "Tasa (%)": round(retenidos / total * 100, 1) if total else 0,
            }
        )

    if retention:
        df_ret = pd.DataFrame(retention)
        fig_ret = px.bar(
            df_ret,
            x="Periodo",
            y="Tasa (%)",
            text=df_ret["Tasa (%)"].apply(lambda v: f"{v:.1f}%"),
            labels={"Tasa (%)": "Tasa de retencion (%)", "Periodo": ""},
            title="Tasa de retencion de clientes",
            color_discrete_sequence=["steelblue"],
        )
        fig_ret.update_traces(textposition="outside")
        fig_ret.update_layout(yaxis_range=[0, 110], height=380)
        st.plotly_chart(fig_ret, width="stretch")
        st.dataframe(df_ret, hide_index=True, width="stretch")
