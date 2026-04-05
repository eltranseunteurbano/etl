"""Predicciones estadisticas — ingresos y riesgo de inasistencia."""

from __future__ import annotations

import sqlite3
import warnings

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

ASISTIO = {"Cliente asistió (default)", "Cliente asistió (Lila)"}
FALTO = {
    "Cliente falta y aviso (verde)",
    "Cliente falta y no avisó (amarillo)",
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

set_browser_tab_title("Predicciones")
st.title("Predicciones")
st.caption(
    "Modelos estadísticos aplicados a los datos del negocio. "
    "Los resultados son estimaciones — no garantías."
)


@st.cache_data
def _load():
    con = sqlite3.connect(DATABASE_PATH)
    df_v = pd.read_sql(
        'SELECT FECHA, VENTAS_POST, "PELUQUERÍA" FROM ventas', con
    )
    df_c = pd.read_sql(
        "SELECT start, color_label FROM calendar_events", con
    )
    con.close()

    df_v["FECHA"] = pd.to_datetime(df_v["FECHA"], format="mixed")
    df_v["VENTAS_POST"] = pd.to_numeric(
        df_v["VENTAS_POST"], errors="coerce"
    ).fillna(0)
    df_v["PELUQUERÍA"] = pd.to_numeric(
        df_v["PELUQUERÍA"], errors="coerce"
    ).fillna(0)

    df_c["start"] = pd.to_datetime(df_c["start"], errors="coerce")
    df_c = df_c.dropna(subset=["start"])

    return df_v, df_c


df_v, df_c = _load()

tab1, tab2 = st.tabs(
    ["📈 Forecast de ingresos", "🚫 Riesgo de inasistencia"]
)

# ── Tab 1: Forecast de ingresos ──────────────────────────────────────────────
with tab1:
    st.subheader("Proyección de ingresos mensuales")
    st.caption(
        "Modelo Holt-Winters (suavizado exponencial). "
        "Se entrena con el historial mensual y proyecta 3 meses hacia adelante. "
        "Si hay 18+ meses de datos, incluye estacionalidad anual."
    )

    fuente = st.selectbox(
        "Fuente de ingresos",
        ["Tienda (VENTAS_POST)", "Peluquería"],
        key="fuente_forecast",
    )
    col_sel = "VENTAS_POST" if "Tienda" in fuente else "PELUQUERÍA"
    color_sel = "steelblue" if "Tienda" in fuente else "coral"
    horizonte = st.slider(
        "Meses a proyectar", min_value=1, max_value=6, value=3
    )

    # Agregación mensual
    df_m = df_v.copy()
    df_m["AÑO"] = df_m["FECHA"].dt.year
    df_m["MES"] = df_m["FECHA"].dt.month
    df_mens = (
        df_m.groupby(["AÑO", "MES"])[col_sel].sum().reset_index()
    )
    df_mens["Fecha"] = pd.to_datetime(
        {"year": df_mens["AÑO"], "month": df_mens["MES"], "day": 1}
    )
    df_mens = df_mens.sort_values("Fecha").reset_index(drop=True)

    # Descartar mes actual si está incompleto
    today = pd.Timestamp.today()
    if (
        df_mens["Fecha"].iloc[-1].month == today.month
        and df_mens["Fecha"].iloc[-1].year == today.year
    ):
        df_mens = df_mens.iloc[:-1]

    n_meses = len(df_mens)

    if n_meses < 6:
        st.warning(
            "Se necesitan al menos 6 meses de datos para proyectar. "
            f"Actualmente hay {n_meses} mes(es)."
        )
    else:
        use_seasonal = n_meses >= 18
        y = df_mens[col_sel].values.astype(float)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if use_seasonal:
                model = ExponentialSmoothing(
                    y,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=12,
                )
            else:
                model = ExponentialSmoothing(y, trend="add")
            fit = model.fit(optimized=True)

        forecast_vals = fit.forecast(horizonte)

        last_date = df_mens["Fecha"].iloc[-1]
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=horizonte,
            freq="MS",
        )

        residuals = y - fit.fittedvalues
        sigma = float(np.std(residuals))
        ci_low = np.maximum(0, forecast_vals - 1.96 * sigma)
        ci_high = forecast_vals + 1.96 * sigma

        # Gráfico
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df_mens["Fecha"],
                y=df_mens[col_sel],
                name="Histórico",
                marker_color=color_sel,
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
        st.plotly_chart(fig, width="stretch")

        # Tabla resumen
        df_fc = pd.DataFrame(
            {
                "Mes": [d.strftime("%B %Y") for d in future_dates],
                "Proyección": [f"${v:,.0f}" for v in forecast_vals],
                "Mínimo (95%)": [f"${v:,.0f}" for v in ci_low],
                "Máximo (95%)": [f"${v:,.0f}" for v in ci_high],
            }
        )
        st.dataframe(df_fc, hide_index=True, width="stretch")

        tipo_modelo = (
            "con estacionalidad anual (12 meses)"
            if use_seasonal
            else "sin estacionalidad — datos insuficientes para ciclo anual"
        )
        st.caption(
            f"Modelo Holt-Winters {tipo_modelo}. "
            f"Entrenado con {n_meses} meses históricos."
        )

# ── Tab 2: Riesgo de inasistencia ────────────────────────────────────────────
with tab2:
    st.subheader("Probabilidad de inasistencia por horario")
    st.caption(
        "Regresión logística entrenada con el historial de citas de Google Calendar. "
        "Estima qué horarios tienen mayor riesgo histórico de inasistencia."
    )

    df_clf = df_c[df_c["color_label"].isin(ASISTIO | FALTO)].copy()
    df_clf["asistio"] = df_clf["color_label"].isin(ASISTIO).astype(int)
    df_clf["hora"] = df_clf["start"].dt.hour
    df_clf["dia_semana"] = df_clf["start"].dt.dayofweek
    df_clf["mes"] = df_clf["start"].dt.month

    features = ["hora", "dia_semana", "mes"]
    n_samples = len(df_clf)
    n_falto = int((df_clf["asistio"] == 0).sum())

    if n_samples < 30:
        st.warning(
            "Se necesitan al menos 30 citas registradas para el modelo. "
            f"Actualmente hay {n_samples}."
        )
    else:
        X = df_clf[features].values
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

        # KPIs
        c1, c2 = st.columns(2)
        c1.metric("Citas analizadas", f"{n_samples:,}")
        c2.metric(
            "Inasistencias históricas",
            f"{n_falto:,} ({n_falto / n_samples * 100:.1f}%)",
        )
        c3, c4 = st.columns(2)
        c3.metric("Exactitud del modelo (CV)", f"{cv_acc * 100:.1f}%")
        c4.metric("Folds de validación", str(n_folds))

        st.divider()

        # Heatmap día × hora con probabilidad de inasistencia
        st.subheader("Mapa de riesgo: día × hora")
        horas = sorted(df_clf["hora"].unique())
        dias = sorted(df_clf["dia_semana"].unique())

        grid = [
            {"dia_semana": d, "hora": h, "mes": 6}
            for d in dias
            for h in horas
        ]
        df_grid = pd.DataFrame(grid)
        X_grid = scaler.transform(df_grid[features].values)
        # Probabilidad de NO asistir = 1 - P(clase 1)
        idx_asistio = list(clf.classes_).index(1)
        proba_falto = 1 - clf.predict_proba(X_grid)[:, idx_asistio]
        df_grid["Riesgo"] = proba_falto

        pivot = df_grid.pivot(
            index="dia_semana", columns="hora", values="Riesgo"
        )
        pivot.index = [DIA_NOMBRES[i] for i in pivot.index]

        fig_heat = px.imshow(
            pivot,
            text_auto=".0%",
            color_continuous_scale="RdYlGn_r",
            zmin=0,
            zmax=1,
            labels={
                "x": "Hora",
                "y": "Día",
                "color": "Riesgo de inasistencia",
            },
            title="Probabilidad estimada de inasistencia por día y hora",
            aspect="auto",
        )
        fig_heat.update_layout(height=380)
        st.plotly_chart(fig_heat, width="stretch")

        st.divider()

        # Importancia de variables (coeficientes)
        st.subheader("¿Qué variable influye más?")
        coefs = pd.DataFrame(
            {
                "Variable": [
                    "Hora del día",
                    "Día de la semana",
                    "Mes del año",
                ],
                "Influencia": np.abs(clf.coef_[0]),
            }
        ).sort_values("Influencia", ascending=True)

        fig_coef = px.bar(
            coefs,
            x="Influencia",
            y="Variable",
            orientation="h",
            title="Peso de cada variable en la predicción",
            color_discrete_sequence=["steelblue"],
            text=coefs["Influencia"].apply(lambda v: f"{v:.3f}"),
        )
        fig_coef.update_traces(textposition="outside")
        fig_coef.update_layout(height=260)
        st.plotly_chart(fig_coef, width="stretch")

        st.caption(
            "Este modelo estima tendencias históricas, no predice el "
            "comportamiento de un cliente específico."
        )
