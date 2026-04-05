"""Predicciones estadisticas — ingresos y riesgo de inasistencia."""

from __future__ import annotations

import sqlite3
import warnings

import holidays as hol_lib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

DIAS_PRE_FESTIVO = 7  # ventana "víspera de festivo"

ASISTIO = {"Cliente asistió (default)", "Cliente asistió (Lila)"}
FALTO = {
    "Cliente falta y aviso (verde)",
    "Cliente falta y no avisó (amarillo)",
}
DIA_NOMBRES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}

set_browser_tab_title("Predicciones")
st.title("Predicciones")
st.caption(
    "Modelos estadísticos aplicados a los datos del negocio. "
    "Los resultados son estimaciones — no garantías."
)

# theme=None evita que el tema Streamlit deje figuras Plotly en blanco en
# algunos navegadores / modos de contraste.
_PLOTLY_KW: dict = {"width": "stretch", "theme": None}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _festivos(years: list[int]) -> dict[pd.Timestamp, str]:
    co = hol_lib.country_holidays("CO", years=years)
    return {pd.Timestamp(d): name for d, name in co.items()}


def _pre_festivos(
    festivos_ts: dict[pd.Timestamp, str], ventana: int
) -> set[pd.Timestamp]:
    """Fechas dentro de `ventana` días antes de cada festivo."""
    result: set[pd.Timestamp] = set()
    for ts in festivos_ts:
        for i in range(1, ventana + 1):
            result.add(ts - pd.Timedelta(days=i))
    return result


@st.cache_data
def _load_db():
    con = sqlite3.connect(DATABASE_PATH)
    df_v = pd.read_sql(
        'SELECT FECHA, VENTAS_POST, "PELUQUERÍA", '
        '"TOTAL VENTAS DÍA" FROM ventas',
        con,
    )
    df_c = pd.read_sql(
        "SELECT start, color_label FROM calendar_events", con
    )
    con.close()

    df_v["FECHA"] = pd.to_datetime(df_v["FECHA"], format="mixed")
    for col in ("VENTAS_POST", "PELUQUERÍA", "TOTAL VENTAS DÍA"):
        df_v[col] = pd.to_numeric(df_v[col], errors="coerce").fillna(0)

    df_c["start"] = pd.to_datetime(df_c["start"], errors="coerce")
    df_c = df_c.dropna(subset=["start"])
    return df_v, df_c


df_v, df_c = _load_db()

tab1, tab2 = st.tabs(
    ["📈 Forecast de ingresos", "🚫 Riesgo de inasistencia"]
)

# ── Tab 1: Forecast de ingresos ──────────────────────────────────────────────
with tab1:
    st.subheader("Proyección de ingresos mensuales")
    st.caption(
        "Modelo Holt-Winters (suavizado exponencial). "
        "Con 18+ meses incluye estacionalidad anual."
    )

    fuente = st.selectbox(
        "Fuente de ingresos",
        ["Tienda (VENTAS_POST)", "Peluquería"],
        key="fuente_forecast",
    )
    col_ing = "VENTAS_POST" if "Tienda" in fuente else "PELUQUERÍA"
    color_ing = "steelblue" if "Tienda" in fuente else "coral"
    horizonte = st.slider(
        "Meses a proyectar", min_value=1, max_value=6, value=3
    )

    df_m = df_v.copy()
    df_m["AÑO"] = df_m["FECHA"].dt.year
    df_m["MES"] = df_m["FECHA"].dt.month
    df_mens = (
        df_m.groupby(["AÑO", "MES"])[col_ing].sum().reset_index()
    )
    df_mens["Fecha"] = pd.to_datetime(
        {"year": df_mens["AÑO"], "month": df_mens["MES"], "day": 1}
    )
    df_mens = df_mens.sort_values("Fecha").reset_index(drop=True)

    today = pd.Timestamp.today()
    if (
        df_mens["Fecha"].iloc[-1].month == today.month
        and df_mens["Fecha"].iloc[-1].year == today.year
    ):
        df_mens = df_mens.iloc[:-1]

    n_meses = len(df_mens)

    if n_meses < 6:
        st.warning(
            f"Se necesitan al menos 6 meses. Actualmente hay {n_meses}."
        )
    else:
        use_seasonal = n_meses >= 18
        y = df_mens[col_ing].values.astype(float)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mdl = ExponentialSmoothing(
                y,
                trend="add",
                seasonal="add" if use_seasonal else None,
                seasonal_periods=12 if use_seasonal else None,
            )
            fit = mdl.fit(optimized=True)

        forecast_vals = fit.forecast(horizonte)
        last_date = df_mens["Fecha"].iloc[-1]
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=horizonte,
            freq="MS",
        )
        sigma = float(np.std(y - fit.fittedvalues))
        ci_low = np.maximum(0.0, forecast_vals - 1.96 * sigma)
        ci_high = forecast_vals + 1.96 * sigma

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df_mens["Fecha"],
                y=df_mens[col_ing],
                name="Histórico",
                marker_color=color_ing,
                opacity=0.7,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df_mens["Fecha"],
                y=fit.fittedvalues,
                name="Modelo ajustado",
                mode="lines",
                line={"color": "dimgray", "width": 1.5, "dash": "dot"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=list(future_dates),
                y=forecast_vals.tolist(),
                name="Proyección",
                mode="lines+markers",
                line={"color": "gold", "width": 2.5},
                marker={"size": 8},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=list(future_dates) + list(future_dates)[::-1],
                y=list(ci_high) + list(ci_low)[::-1],
                fill="toself",
                fillcolor="rgba(255,215,0,0.15)",
                line={"color": "rgba(0,0,0,0)"},
                name="Intervalo 95%",
            )
        )
        fig.update_layout(
            title=f"Proyección mensual — {fuente}",
            xaxis_title="Mes",
            yaxis_title="COP",
            height=460,
            legend={"orientation": "h", "y": -0.22},
        )
        st.plotly_chart(fig, **_PLOTLY_KW)

        df_fc = pd.DataFrame(
            {
                "Mes": [d.strftime("%B %Y") for d in future_dates],
                "Proyección": [f"${v:,.0f}" for v in forecast_vals],
                "Mínimo (95%)": [f"${v:,.0f}" for v in ci_low],
                "Máximo (95%)": [f"${v:,.0f}" for v in ci_high],
            }
        )
        st.dataframe(df_fc, hide_index=True, width="stretch")

        tipo = (
            "con estacionalidad anual"
            if use_seasonal
            else "sin estacionalidad (menos de 18 meses)"
        )
        st.caption(f"Holt-Winters {tipo}. {n_meses} meses históricos.")

    st.divider()

    # Ventas en días previos a festivo
    st.subheader("¿Suben las ventas antes de los festivos?")
    st.caption(
        f"Compara la venta diaria en los {DIAS_PRE_FESTIVO} días previos "
        "a un festivo colombiano versus el resto del año."
    )

    years_v = df_v["FECHA"].dt.year.unique().tolist()
    fest_map = _festivos(years_v)
    pre_fest_set = _pre_festivos(fest_map, DIAS_PRE_FESTIVO)

    df_vd = df_v[df_v["TOTAL VENTAS DÍA"] > 0].copy()
    df_vd["fecha_norm"] = df_vd["FECHA"].dt.normalize()
    df_vd["es_pre_festivo"] = df_vd["fecha_norm"].isin(pre_fest_set)
    df_vd["es_festivo"] = df_vd["fecha_norm"].isin(fest_map)

    df_vd["Periodo"] = "Día normal"
    df_vd.loc[df_vd["es_pre_festivo"], "Periodo"] = (
        f"Pre-festivo (≤{DIAS_PRE_FESTIVO} días antes)"
    )
    df_vd.loc[df_vd["es_festivo"], "Periodo"] = "Día festivo"

    med_periodo = (
        df_vd.groupby("Periodo")["TOTAL VENTAS DÍA"]
        .median()
        .reset_index()
        .rename(columns={"TOTAL VENTAS DÍA": "Mediana ventas"})
    )
    orden = [
        "Día normal",
        f"Pre-festivo (≤{DIAS_PRE_FESTIVO} días antes)",
        "Día festivo",
    ]
    med_periodo["Periodo"] = pd.Categorical(
        med_periodo["Periodo"], categories=orden, ordered=True
    )
    med_periodo = med_periodo.sort_values("Periodo")

    fig_pf = px.bar(
        med_periodo,
        x="Periodo",
        y="Mediana ventas",
        color="Periodo",
        text=med_periodo["Mediana ventas"].apply(lambda v: f"${v:,.0f}"),
        color_discrete_map={
            "Día normal": "steelblue",
            f"Pre-festivo (≤{DIAS_PRE_FESTIVO} días antes)": "coral",
            "Día festivo": "dimgray",
        },
        labels={"Mediana ventas": "Mediana ventas diarias (COP)"},
        title="Mediana de ventas diarias por tipo de día",
    )
    fig_pf.update_traces(textposition="outside")
    fig_pf.update_layout(
        showlegend=False,
        height=360,
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
    )
    st.plotly_chart(fig_pf, **_PLOTLY_KW)

    # Desglose por festivo importante
    st.subheader("Top festivos con mayor impacto en ventas")
    # Construir tabla: para cada día pre-festivo, ¿qué festivo precede?
    rows = []
    for _, row in df_vd[df_vd["es_pre_festivo"]].iterrows():
        fecha = row["fecha_norm"]
        for i in range(1, DIAS_PRE_FESTIVO + 1):
            nombre = fest_map.get(fecha + pd.Timedelta(days=i))
            if nombre:
                rows.append(
                    {
                        "Festivo": nombre,
                        "ventas": row["TOTAL VENTAS DÍA"],
                    }
                )
                break

    if rows:
        df_rows = pd.DataFrame(rows)
        top_fest = (
            df_rows.groupby("Festivo")["ventas"]
            .median()
            .nlargest(10)
            .reset_index()
            .rename(columns={"ventas": "Mediana ventas pre-festivo"})
        )
        fig_tf = px.bar(
            top_fest,
            x="Mediana ventas pre-festivo",
            y="Festivo",
            orientation="h",
            text=top_fest["Mediana ventas pre-festivo"].apply(
                lambda v: f"${v:,.0f}"
            ),
            color_discrete_sequence=["coral"],
            title="Top 10 festivos por ventas en víspera",
        )
        fig_tf.update_traces(textposition="outside")
        fig_tf.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=400,
            xaxis_tickprefix="$",
            xaxis_tickformat=",",
        )
        st.plotly_chart(fig_tf, **_PLOTLY_KW)

# ── Tab 2: Riesgo de inasistencia ────────────────────────────────────────────
with tab2:
    st.subheader("Probabilidad de inasistencia")
    st.caption(
        "Regresión logística entrenada con el historial de Google Calendar "
        "y festivos de Colombia."
    )

    df_clf = df_c[df_c["color_label"].isin(ASISTIO | FALTO)].copy()
    df_clf["asistio"] = df_clf["color_label"].isin(ASISTIO).astype(int)
    _starts = df_clf["start"]
    if _starts.dt.tz is not None:
        _starts = _starts.dt.tz_convert("America/Bogota")
    df_clf["fecha"] = pd.to_datetime(
        _starts.dt.normalize().dt.strftime("%Y-%m-%d")
    )
    df_clf["hora"] = df_clf["start"].dt.hour
    df_clf["dia_semana"] = df_clf["start"].dt.dayofweek
    df_clf["mes"] = df_clf["start"].dt.month

    n_samples = len(df_clf)

    if n_samples < 30:
        st.warning(
            f"Se necesitan al menos 30 citas. Hay {n_samples}."
        )
        st.stop()

    # Festivos y pre-festivos
    years_c = df_clf["fecha"].dt.year.unique().tolist()
    fest_map_c = _festivos(years_c)
    pre_fest_c = _pre_festivos(fest_map_c, DIAS_PRE_FESTIVO)
    df_clf["es_festivo"] = df_clf["fecha"].isin(fest_map_c).astype(int)
    df_clf["es_pre_festivo"] = df_clf["fecha"].isin(pre_fest_c).astype(int)

    features = ["hora", "dia_semana", "mes", "es_festivo", "es_pre_festivo"]

    X = df_clf[features].values.astype(float)
    y_clf = df_clf["asistio"].values

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    clf = LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=42
    )
    clf.fit(X_sc, y_clf)

    n_folds = min(5, max(2, n_samples // 20))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cv_acc = cross_val_score(
            clf, X_sc, y_clf, cv=n_folds, scoring="accuracy"
        ).mean()

    n_falto = int(np.sum(y_clf == 0))
    n_fest_citas = int(df_clf["es_festivo"].sum())
    n_pre_citas = int(df_clf["es_pre_festivo"].sum())

    # KPIs
    c1, c2 = st.columns(2)
    c1.metric("Citas analizadas", f"{n_samples:,}")
    c2.metric(
        "Inasistencias",
        f"{n_falto:,} ({n_falto / n_samples * 100:.1f}%)",
    )
    c3, c4 = st.columns(2)
    c3.metric("Exactitud del modelo (CV)", f"{cv_acc * 100:.1f}%")
    c4.metric(
        "Citas pre-festivo / festivo",
        f"{n_pre_citas:,} / {n_fest_citas:,}",
    )

    st.divider()

    # Mapa de riesgo día × hora
    st.subheader("Mapa de riesgo: día × hora")
    st.caption("Día normal, sin festivo.")

    horas = sorted(df_clf["hora"].unique())
    dias = sorted(df_clf["dia_semana"].unique())
    grid = [
        {
            "dia_semana": d,
            "hora": h,
            "mes": 6,
            "es_festivo": 0,
            "es_pre_festivo": 0,
        }
        for d in dias
        for h in horas
    ]
    df_grid = pd.DataFrame(grid)
    X_grid = scaler.transform(df_grid[features].values.astype(float))
    idx_asistio = list(clf.classes_).index(1)
    df_grid["Riesgo"] = 1 - clf.predict_proba(X_grid)[:, idx_asistio]

    pivot = df_grid.pivot(
        index="dia_semana", columns="hora", values="Riesgo"
    )
    pivot.index = pd.Index([DIA_NOMBRES[int(i)] for i in pivot.index])

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn_r",
        zmin=0,
        zmax=1,
        labels={"x": "Hora", "y": "Día", "color": "Riesgo"},
        title="Probabilidad estimada de inasistencia por día y hora",
        aspect="auto",
    )
    fig_heat.update_traces(
        text=[[f"{v:.0%}" for v in row] for row in pivot.values],
        texttemplate="%{text}",
    )
    fig_heat.update_layout(height=380)
    st.plotly_chart(fig_heat, **_PLOTLY_KW)

    st.divider()

    # Efecto de festivos y pre-festivos en asistencia
    st.subheader("Festivos y pre-festivos: ¿afectan la asistencia?")

    df_clf["Tipo de día"] = "Día normal"
    df_clf.loc[df_clf["es_pre_festivo"] == 1, "Tipo de día"] = (
        "Pre-festivo"
    )
    df_clf.loc[df_clf["es_festivo"] == 1, "Tipo de día"] = "Festivo"

    tipo_stats = (
        df_clf.groupby("Tipo de día")["asistio"]
        .agg(citas="count", asistieron="sum")
        .reset_index()
    )
    tipo_stats["Tasa inasistencia"] = (
        1 - tipo_stats["asistieron"] / tipo_stats["citas"]
    )

    fig_tipo = px.bar(
        tipo_stats,
        x="Tipo de día",
        y="Tasa inasistencia",
        text=tipo_stats["Tasa inasistencia"].apply(lambda v: f"{v:.1%}"),
        color="Tipo de día",
        color_discrete_map={
            "Día normal": "steelblue",
            "Pre-festivo": "coral",
            "Festivo": "dimgray",
        },
        labels={"Tasa inasistencia": "Tasa de inasistencia"},
        title="Inasistencia según tipo de día",
    )
    fig_tipo.update_traces(textposition="outside")
    fig_tipo.update_layout(
        yaxis_tickformat=".0%", height=340, showlegend=False
    )
    st.plotly_chart(fig_tipo, **_PLOTLY_KW)

    st.divider()

    # Importancia de variables
    st.subheader("¿Qué variable influye más?")
    nombres = {
        "hora": "Hora del día",
        "dia_semana": "Día de la semana",
        "mes": "Mes del año",
        "es_festivo": "Día festivo",
        "es_pre_festivo": "Víspera de festivo",
    }
    coefs = pd.DataFrame(
        {
            "Variable": [nombres[f] for f in features],
            "Influencia": np.abs(clf.coef_[0]),
        }
    ).sort_values("Influencia", ascending=True)

    fig_coef = px.bar(
        coefs,
        x="Influencia",
        y="Variable",
        orientation="h",
        text=coefs["Influencia"].apply(lambda v: f"{v:.3f}"),
        color_discrete_sequence=["steelblue"],
        title="Peso de cada variable en la predicción de inasistencia",
    )
    fig_coef.update_traces(textposition="outside")
    fig_coef.update_layout(height=320)
    st.plotly_chart(fig_coef, **_PLOTLY_KW)

    st.caption(
        "Festivos: holidays.country_holidays('CO'). "
        f"Pre-festivo: {DIAS_PRE_FESTIVO} días antes del festivo."
    )
