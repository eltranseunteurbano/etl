import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

set_browser_tab_title("Tienda", "Ventas")
st.title("Tienda · Ventas")

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

NUMERIC_COLS = [
    "VENTAS_PRE",
    "IVA",
    "VENTAS_POST",
    "TOTAL VENTAS DÍA",
    "PELUQUERÍA",
]

COL_LABELS = {
    "VENTAS_PRE": "Ventas antes IVA",
    "IVA": "IVA",
    "VENTAS_POST": "Ventas post IVA",
    "TOTAL VENTAS DÍA": "Total ventas día",
    "PELUQUERÍA": "Peluquería",
}


@st.cache_data
def _load_ventas() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql(
        "SELECT * FROM ventas ORDER BY FECHA", con, parse_dates=["FECHA"]
    )
    con.close()
    df["AÑO"] = df["FECHA"].dt.year
    df["MES"] = df["FECHA"].dt.month
    df["DIA_SEMANA"] = df["FECHA"].dt.dayofweek
    df["MA7"] = df["TOTAL VENTAS DÍA"].rolling(7).median()
    df["MA30"] = df["TOTAL VENTAS DÍA"].rolling(30).median()
    return df


df = _load_ventas()
col_ventas = "TOTAL VENTAS DÍA"

# ── Métricas rápidas ────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Días registrados", f"{len(df):,}")
c2.metric("Mediana diaria", f"${df[col_ventas].median():,.0f}")
c3.metric("Mejor día", f"${df[col_ventas].max():,.0f}")
c4.metric("Día más bajo", f"${df[col_ventas].min():,.0f}")

st.divider()

# ── Pestañas ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "📊 Estadísticos",
        "📈 Distribución",
        "🔗 Relación entre variables",
        "📅 Por año",
        "📉 Tendencia",
        "🧩 Composición",
    ]
)

# ── Tab 1: Estadísticos descriptivos ────────────────────────────────────────
with tab1:
    st.subheader("Estadísticos descriptivos — Total ventas día")

    desc = df[col_ventas].describe()
    stats = {
        "Registros": int(desc["count"]),
        "Promedio": desc["mean"],
        "Mediana": desc["50%"],
        "Desviación estándar": desc["std"],
        "Mínimo": desc["min"],
        "Percentil 25%": desc["25%"],
        "Percentil 75%": desc["75%"],
        "Máximo": desc["max"],
        "Asimetría (skewness)": df[col_ventas].skew(),
        "Curtosis (kurtosis)": df[col_ventas].kurt(),
    }

    fmt_stats = {}
    for k, v in stats.items():
        if k == "Registros":
            fmt_stats[k] = f"{v:,}"
        elif k in ("Asimetría (skewness)", "Curtosis (kurtosis)"):
            fmt_stats[k] = f"{v:.4f}"
        else:
            fmt_stats[k] = f"${v:,.0f}"

    stats_df = pd.DataFrame(
        {
            "Estadístico": list(fmt_stats.keys()),
            "Valor": list(fmt_stats.values()),
        }
    )
    st.dataframe(stats_df, hide_index=True, width="stretch")
    st.caption(
        "Asimetría positiva indica cola derecha (días con ventas muy altas). "
        "Curtosis > 3 indica distribución más apuntada que la normal."
    )

    st.divider()
    st.subheader("Días atípicos")

    def _fmt_outliers(sub: pd.DataFrame) -> pd.DataFrame:
        out = sub[["FECHA", col_ventas]].copy()
        out["Día"] = sub["DIA_SEMANA"].map(DIA_NOMBRES)
        out["Mes"] = sub["MES"].map(MES_NOMBRES)
        out["Fecha"] = out["FECHA"].dt.strftime("%d/%m/%Y")
        out["Total"] = out[col_ventas].apply(lambda v: f"${v:,.0f}")
        return out[["Fecha", "Día", "Mes", "Total"]]

    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Top 10 días con mayores ventas**")
        st.dataframe(
            _fmt_outliers(df.nlargest(10, col_ventas)),
            hide_index=True,
            width="stretch",
        )
    with cb:
        st.markdown("**Top 10 días con menores ventas**")
        st.dataframe(
            _fmt_outliers(df.nsmallest(10, col_ventas)),
            hide_index=True,
            width="stretch",
        )

# ── Tab 2: Distribución ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Distribución de ventas diarias")

    p99 = df[col_ventas].quantile(0.99)
    outliers = df[df[col_ventas] > p99]
    n_out = len(outliers)

    fig_hist = px.histogram(
        df[df[col_ventas] <= p99],
        x=col_ventas,
        marginal="rug",
        labels={col_ventas: "Total ventas día (COP)"},
        title="Distribución de ventas diarias",
        hover_data=[col_ventas],
    )
    fig_hist.update_layout(bargap=0.05)
    st.plotly_chart(fig_hist, width="stretch")

    st.caption(
        f"{n_out} días con ventas > ${p99:,.0f} (percentil 99) no se "
        f"muestran en el gráfico. Rango de esos días: p."
    )

    fig_box = px.box(
        df,
        x="AÑO",
        y=col_ventas,
        labels={col_ventas: "Total ventas día (COP)", "AÑO": "Año"},
        title="Distribución por año (box plot)",
    )
    st.plotly_chart(fig_box, width="stretch")

    df_mes = df.copy()
    df_mes["Mes"] = df_mes["MES"].map(MES_NOMBRES)
    orden_meses = list(MES_NOMBRES.values())
    fig_box_mes = px.box(
        df_mes,
        x="Mes",
        y=col_ventas,
        category_orders={"Mes": orden_meses},
        labels={col_ventas: "Total ventas día (COP)", "Mes": ""},
        title="Distribución por mes (box plot)",
    )
    st.plotly_chart(fig_box_mes, width="stretch")

    df_dia = df.copy()
    df_dia["Día"] = df_dia["DIA_SEMANA"].map(DIA_NOMBRES)
    orden_dias = list(DIA_NOMBRES.values())
    fig_box_dia = px.box(
        df_dia,
        x="Día",
        y=col_ventas,
        category_orders={"Día": orden_dias},
        labels={col_ventas: "Total ventas día (COP)", "Día": ""},
        title="Distribución por día de la semana (box plot)",
    )
    st.plotly_chart(fig_box_dia, width="stretch")

# ── Tab 3: Relación entre variables ─────────────────────────────────────────
with tab3:
    st.subheader("Correlación entre variables")

    corr = df[NUMERIC_COLS].corr()
    labels = [COL_LABELS[c] for c in NUMERIC_COLS]

    fig_heatmap = px.imshow(
        corr,
        x=labels,
        y=labels,
        text_auto=True,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Mapa de correlación (Pearson)",
    )
    st.plotly_chart(fig_heatmap, width="stretch")

    st.subheader("Matriz de dispersión")
    fig_scatter = px.scatter_matrix(
        df,
        dimensions=NUMERIC_COLS,
        labels=COL_LABELS,
        title="Dispersión entre variables numéricas",
        opacity=0.4,
    )
    fig_scatter.update_traces(marker_size=4)
    fig_scatter.update_layout(height=800)
    st.plotly_chart(fig_scatter, width="stretch")

# ── Tab 4: Estadísticos por año ─────────────────────────────────────────────
with tab4:
    years = sorted(df["AÑO"].unique())

    st.subheader("Meses ordenados por mediana de ventas")
    for year in years:
        df_year = df[df["AÑO"] == year].copy()
        resumen_meses = (
            df_year.groupby("MES")[col_ventas]
            .agg(["median", "sum", "count"])
            .reset_index()
            .rename(
                columns={"median": "Mediana", "sum": "Total", "count": "Días"}
            )
            .sort_values("Mediana", ascending=False)
        )
        resumen_meses["Mes"] = resumen_meses["MES"].map(MES_NOMBRES)

        with st.expander(f"**{year}**", expanded=True):
            fig_meses = px.bar(
                resumen_meses,
                x="Mediana",
                y="Mes",
                orientation="h",
                text=resumen_meses["Mediana"].apply(lambda v: f"${v:,.0f}"),
                labels={"Mediana": "Mediana ventas día (COP)", "Mes": ""},
                title=f"Mediana diaria por mes — {year}",
            )
            fig_meses.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_meses, width="stretch")

            tabla_meses = resumen_meses[
                ["Mes", "Mediana", "Total", "Días"]
            ].copy()
            tabla_meses["Mediana"] = tabla_meses["Mediana"].apply(
                lambda v: f"${v:,.0f}"
            )
            tabla_meses["Total"] = tabla_meses["Total"].apply(
                lambda v: f"${v:,.0f}"
            )
            st.dataframe(tabla_meses, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Días de la semana ordenados por mediana de ventas")
    for year in years:
        df_year = df[df["AÑO"] == year].copy()
        resumen_dias = (
            df_year.groupby("DIA_SEMANA")[col_ventas]
            .agg(["median", "count"])
            .reset_index()
            .rename(columns={"median": "Mediana", "count": "Días"})
            .sort_values("Mediana", ascending=False)
        )
        resumen_dias["Día"] = resumen_dias["DIA_SEMANA"].map(DIA_NOMBRES)

        with st.expander(f"**{year}**", expanded=True):
            fig_dias = px.bar(
                resumen_dias,
                x="Mediana",
                y="Día",
                orientation="h",
                text=resumen_dias["Mediana"].apply(lambda v: f"${v:,.0f}"),
                labels={"Mediana": "Mediana ventas día (COP)", "Día": ""},
                title=f"Mediana diaria por día de semana — {year}",
            )
            fig_dias.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_dias, width="stretch")

            tabla_dias = resumen_dias[["Día", "Mediana", "Días"]].copy()
            tabla_dias["Mediana"] = tabla_dias["Mediana"].apply(
                lambda v: f"${v:,.0f}"
            )
            st.dataframe(tabla_dias, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Meses con más días atípicos por año")
    st.caption(
        "Un día es atípico si su venta está fuera del rango "
        "Q1 − 1.5×IQR  o  Q3 + 1.5×IQR calculado para ese año."
    )

    for year in years:
        df_year = df[df["AÑO"] == year].copy()
        q1 = df_year[col_ventas].quantile(0.25)
        q3 = df_year[col_ventas].quantile(0.75)
        iqr = q3 - q1
        limite_inf = q1 - 1.5 * iqr
        limite_sup = q3 + 1.5 * iqr

        df_out = df_year[
            (df_year[col_ventas] < limite_inf)
            | (df_year[col_ventas] > limite_sup)
        ].copy()
        df_out["Tipo"] = df_out[col_ventas].apply(
            lambda v: "Alto" if v > limite_sup else "Bajo"
        )

        conteo = (
            df_out.groupby("MES")
            .agg(
                Atípicos=("MES", "count"),
                Altos=("Tipo", lambda x: (x == "Alto").sum()),
                Bajos=("Tipo", lambda x: (x == "Bajo").sum()),
            )
            .reset_index()
            .sort_values("Atípicos", ascending=False)
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
                    y="Atípicos",
                    color="Altos",
                    text="Atípicos",
                    labels={
                        "Atípicos": "Días atípicos",
                        "Mes": "",
                        "Altos": "Días altos",
                    },
                    title=f"Días atípicos por mes — {year}",
                    color_continuous_scale="OrRd",
                    category_orders={
                        "Mes": [MES_NOMBRES[m] for m in sorted(conteo["MES"])]
                    },
                )
                st.plotly_chart(fig_out, width="stretch")

                tabla_out = conteo[["Mes", "Atípicos", "Altos", "Bajos"]]
                st.dataframe(tabla_out, hide_index=True, width="stretch")

# ── Tab 5: Serie de tiempo con tendencia ─────────────────────────────────────
with tab5:
    st.subheader("Evolución de ventas en el tiempo")

    fig_serie = go.Figure()
    fig_serie.add_trace(
        go.Scatter(
            x=df["FECHA"],
            y=df[col_ventas],
            mode="lines",
            name="Ventas diarias",
            line={"color": "lightsteelblue", "width": 1},
            opacity=0.6,
        )
    )
    fig_serie.add_trace(
        go.Scatter(
            x=df["FECHA"],
            y=df["MA7"],
            mode="lines",
            name="Mediana móvil 7 días",
            line={"color": "steelblue", "width": 2},
        )
    )
    fig_serie.add_trace(
        go.Scatter(
            x=df["FECHA"],
            y=df["MA30"],
            mode="lines",
            name="Mediana móvil 30 días",
            line={"color": "firebrick", "width": 2.5},
        )
    )
    fig_serie.update_layout(
        title="Ventas diarias con tendencia móvil",
        xaxis_title="Fecha",
        yaxis_title="Total ventas día (COP)",
        legend={"orientation": "h", "y": -0.15},
        height=550,
    )
    st.plotly_chart(fig_serie, width="stretch")
    st.caption(
        "La mediana móvil de 30 días suaviza el ruido diario y revela la "
        "tendencia general del negocio."
    )

# ── Tab 6: Composición tienda vs peluquería ──────────────────────────────────
with tab6:
    st.subheader("Composición de ingresos: Tienda vs Peluquería")

    # Proporción global
    total_tienda = df["VENTAS_POST"].sum()
    total_pelu = df["PELUQUERÍA"].sum()
    fig_pie = px.pie(
        names=["Tienda", "Peluquería"],
        values=[total_tienda, total_pelu],
        title="Proporción global de ingresos",
        color_discrete_sequence=["steelblue", "coral"],
    )
    st.plotly_chart(fig_pie, width="stretch")

    # Área apilada por mes
    df_comp = (
        df.groupby(["AÑO", "MES"])[["VENTAS_POST", "PELUQUERÍA"]]
        .sum()
        .reset_index()
    )
    df_comp["Fecha"] = pd.to_datetime(
        {"year": df_comp["AÑO"], "month": df_comp["MES"], "day": 1}
    )
    df_comp = df_comp.sort_values("Fecha")

    fig_area = go.Figure()
    fig_area.add_trace(
        go.Scatter(
            x=df_comp["Fecha"],
            y=df_comp["VENTAS_POST"],
            name="Tienda",
            stackgroup="one",
            fill="tonexty",
            line={"color": "steelblue"},
        )
    )
    fig_area.add_trace(
        go.Scatter(
            x=df_comp["Fecha"],
            y=df_comp["PELUQUERÍA"],
            name="Peluquería",
            stackgroup="one",
            fill="tonexty",
            line={"color": "coral"},
        )
    )
    fig_area.update_layout(
        title="Ingresos mensuales acumulados por fuente",
        xaxis_title="Mes",
        yaxis_title="Total (COP)",
        legend={"orientation": "h", "y": -0.15},
    )
    st.plotly_chart(fig_area, width="stretch")
