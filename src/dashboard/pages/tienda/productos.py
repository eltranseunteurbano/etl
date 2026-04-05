"""Dashboard de productos de la tienda."""

import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.config.settings import DATABASE_PATH
from src.dashboard.utils import set_browser_tab_title

set_browser_tab_title("Tienda", "Productos")
st.title("Tienda · Productos")

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


@st.cache_data
def _load_productos() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql("SELECT * FROM alegra_productos", con)
    con.close()
    return df


@st.cache_data
def _load_facturas() -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql(
        "SELECT * FROM alegra_facturas ORDER BY date",
        con,
        parse_dates=["date"],
    )
    con.close()
    df["AÑO"] = df["date"].dt.year
    df["MES"] = df["date"].dt.month
    return df


df_prod = _load_productos()
df_fact = _load_facturas()

df_activos = df_prod[df_prod["status"] == "active"].copy()
df_con_ventas = df_prod[df_prod["total_revenue"] > 0].copy()

# ── Métricas rápidas ────────────────────────────────────────────────────────
total_activos = len(df_activos)
total_revenue = df_prod["total_revenue"].sum()
top_prod_name = df_prod.loc[df_prod["total_revenue"].idxmax(), "name"]
total_facturas = df_fact["id"].nunique()

c1, c2 = st.columns(2)
c1.metric("Productos activos", f"{total_activos:,}")
c2.metric("Revenue total (facturas)", f"${total_revenue:,.0f}")
label = (
    top_prod_name[:28] + "…"
    if isinstance(top_prod_name, str) and len(top_prod_name) > 28
    else top_prod_name
)
c3, c4 = st.columns(2)
c3.metric("Facturas registradas", f"{total_facturas:,}")
c4.metric("Producto líder", str(label or ""))

st.divider()

# ── Pestañas ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Ranking",
        "📈 Distribución de precios",
        "📦 Inventario",
        "🗓 Ventas en el tiempo",
        "🔍 Análisis",
    ]
)

# ── Tab 1: Ranking ───────────────────────────────────────────────────────────
with tab1:
    n = 10

    st.subheader("Top 10 productos por revenue")
    top_rev = df_con_ventas.nlargest(10, "total_revenue")[
        ["name", "total_revenue", "total_sold_quantity", "price"]
    ].copy()
    fig_rev = px.bar(
        top_rev,
        x="total_revenue",
        y="name",
        orientation="h",
        text=top_rev["total_revenue"].apply(lambda v: f"${v:,.0f}"),
        labels={
            "total_revenue": "Revenue total (COP)",
            "name": "",
        },
        title=f"Top {n} por revenue",
    )
    fig_rev.update_layout(
        yaxis={"categoryorder": "total ascending"}, height=520
    )
    st.plotly_chart(fig_rev, width="stretch")

    st.subheader("Top 10 productos por unidades vendidas")
    top_qty = df_con_ventas.nlargest(10, "total_sold_quantity")[
        ["name", "total_sold_quantity", "total_revenue", "price"]
    ].copy()
    fig_qty = px.bar(
        top_qty,
        x="total_sold_quantity",
        y="name",
        orientation="h",
        text=top_qty["total_sold_quantity"].apply(lambda v: f"{v:,.0f}"),
        labels={
            "total_sold_quantity": "Unidades vendidas",
            "name": "",
        },
        title="Top 10 por unidades vendidas",
    )
    fig_qty.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=520,
    )
    st.plotly_chart(fig_qty, width="stretch")

    st.subheader("Tabla completa de productos con ventas")
    tabla = df_con_ventas[
        [
            "name",
            "status",
            "price",
            "iva_percentage",
            "total_sold_quantity",
            "total_revenue",
        ]
    ].copy()
    tabla = tabla.sort_values("total_revenue", ascending=False)
    tabla.columns = [
        "Producto",
        "Estado",
        "Precio",
        "IVA %",
        "Unidades vendidas",
        "Revenue",
    ]
    tabla["Precio"] = tabla["Precio"].apply(lambda v: f"${v:,.0f}")
    tabla["Revenue"] = tabla["Revenue"].apply(lambda v: f"${v:,.0f}")
    tabla["Unidades vendidas"] = tabla["Unidades vendidas"].apply(
        lambda v: f"{v:,.0f}"
    )
    st.dataframe(tabla, hide_index=True, width="stretch")

# ── Tab 2: Distribución de precios ───────────────────────────────────────────
with tab2:
    st.subheader("Distribución de precios de productos activos")

    precios = df_activos[df_activos["price"] > 0]["price"]
    p99 = precios.quantile(0.99)
    outliers_precio = precios[precios > p99]
    n_out = len(outliers_precio)

    fig_hist = px.histogram(
        precios[precios <= p99].rename("Precio (COP)"),
        x="Precio (COP)",
        nbins=40,
        marginal="rug",
        labels={"Precio (COP)": "Precio unitario (COP)"},
        title="Distribución de precios — productos activos",
    )
    fig_hist.update_layout(bargap=0.05)
    st.plotly_chart(fig_hist, width="stretch")

    if n_out > 0:
        st.caption(
            f"{n_out} productos con precio > ${p99:,.0f} (percentil 99)."
            f" - Mediana: ${precios.median():,.0f}."
        )

    st.divider()
    st.subheader("Distribución de revenue por producto")

    revenue = df_con_ventas["total_revenue"]
    p99_rev = revenue.quantile(0.99)
    out_rev = revenue[revenue > p99_rev]
    n_out_rev = len(out_rev)

    fig_hist_rev = px.histogram(
        revenue[revenue <= p99_rev].rename("Revenue (COP)"),
        x="Revenue (COP)",
        nbins=40,
        marginal="rug",
        labels={"Revenue (COP)": "Revenue total por producto (COP)"},
        title="Distribución de revenue — productos con ventas",
    )
    fig_hist_rev.update_layout(bargap=0.05)
    st.plotly_chart(fig_hist_rev, width="stretch")

    if n_out_rev > 0:
        rango_rev = f"${out_rev.min():,.0f} – ${out_rev.max():,.0f}"
        st.caption(
            f"{n_out_rev} productos con revenue > ${p99_rev:,.0f} (percentil 99) "
            f"no se muestran. Rango: {rango_rev}. "
            f"Mediana: ${revenue.median():,.0f}."
        )

    st.divider()
    st.subheader("Productos por tasa de IVA")
    iva_counts = (
        df_activos.groupby("iva_percentage")
        .agg(
            Productos=("id", "count"),
            Revenue=("total_revenue", "sum"),
        )
        .reset_index()
        .rename(columns={"iva_percentage": "IVA %"})
        .sort_values("Productos", ascending=False)
    )
    col_a, col_b = st.columns(2)
    with col_a:
        fig_iva = px.pie(
            iva_counts,
            names="IVA %",
            values="Productos",
            title="Productos por tasa de IVA",
        )
        st.plotly_chart(fig_iva, width="stretch")
    with col_b:
        fig_iva_rev = px.pie(
            iva_counts,
            names="IVA %",
            values="Revenue",
            title="Revenue por tasa de IVA",
        )
        st.plotly_chart(fig_iva_rev, width="stretch")

# ── Tab 3: Inventario ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Estado del inventario")

    col_e, col_f = st.columns(2)
    with col_e:
        status_counts = (
            df_prod.groupby("status")
            .agg(Productos=("id", "count"))
            .reset_index()
            .rename(columns={"status": "Estado"})
        )
        status_counts["Estado"] = (
            status_counts["Estado"]
            .map({"active": "Activo", "inactive": "Inactivo"})
            .fillna(status_counts["Estado"])
        )
        fig_status = px.pie(
            status_counts,
            names="Estado",
            values="Productos",
            title="Activos vs Inactivos",
            color_discrete_map={
                "Activo": "steelblue",
                "Inactivo": "lightgray",
            },
        )
        st.plotly_chart(fig_status, width="stretch")

    with col_f:
        sin_stock = len(df_activos[df_activos["available_quantity"] <= 0])
        con_stock = len(df_activos[df_activos["available_quantity"] > 0])
        fig_stock = px.pie(
            names=["Con stock", "Sin stock / negativo"],
            values=[con_stock, sin_stock],
            title="Stock disponible — productos activos",
            color_discrete_sequence=["steelblue", "coral"],
        )
        st.plotly_chart(fig_stock, width="stretch")

    st.divider()
    st.subheader("Productos activos con stock negativo")
    df_neg = (
        df_activos[df_activos["available_quantity"] < 0][
            [
                "name",
                "price",
                "available_quantity",
                "total_sold_quantity",
                "total_revenue",
            ]
        ]
        .copy()
        .sort_values("available_quantity")
    )
    if df_neg.empty:
        st.info("No hay productos con stock negativo.")
    else:
        df_neg.columns = [
            "Producto",
            "Precio",
            "Stock disponible",
            "Unidades vendidas",
            "Revenue",
        ]
        df_neg["Precio"] = df_neg["Precio"].apply(lambda v: f"${v:,.0f}")
        df_neg["Unidades vendidas"] = df_neg["Unidades vendidas"].apply(
            lambda v: f"{v:,.0f}"
        )
        st.dataframe(df_neg, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Top 10 productos activos con mayor stock")
    df_top_stock = (
        df_activos[df_activos["available_quantity"] > 0]
        .nlargest(10, "available_quantity")[
            ["name", "available_quantity", "price", "total_sold_quantity"]
        ]
        .copy()
    )
    fig_top_stock = px.bar(
        df_top_stock,
        x="available_quantity",
        y="name",
        orientation="h",
        text=df_top_stock["available_quantity"].apply(lambda v: f"{v:,.0f}"),
        labels={
            "available_quantity": "Unidades disponibles",
            "name": "",
        },
        title="Top 10 productos con mayor stock disponible",
    )
    fig_top_stock.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=520,
    )
    st.plotly_chart(fig_top_stock, width="stretch")

# ── Tab 4: Ventas en el tiempo ───────────────────────────────────────────────
with tab4:
    st.subheader("Revenue mensual (facturas)")

    df_mens = (
        df_fact.groupby(["AÑO", "MES"])
        .agg(
            Revenue=("total_product", "sum"),
            Facturas=("id", "nunique"),
            Lineas=("id", "count"),
        )
        .reset_index()
    )
    df_mens["Fecha"] = pd.to_datetime(
        {"year": df_mens["AÑO"], "month": df_mens["MES"], "day": 1}
    )
    df_mens = df_mens.sort_values("Fecha")
    df_mens["Mes"] = df_mens["MES"].map(MES_NOMBRES)

    fig_rev_mens = go.Figure()
    fig_rev_mens.add_trace(
        go.Bar(
            x=df_mens["Fecha"],
            y=df_mens["Revenue"],
            name="Revenue",
            marker_color="steelblue",
            text=df_mens["Revenue"].apply(lambda v: f"${v / 1e6:.1f}M"),
            textposition="outside",
        )
    )
    fig_rev_mens.update_layout(
        title="Revenue mensual de productos",
        xaxis_title="Mes",
        yaxis_title="Revenue (COP)",
        height=520,
    )
    st.plotly_chart(fig_rev_mens, width="stretch")

    st.subheader("Facturas por mes")
    fig_fact_mens = px.bar(
        df_mens,
        x="Fecha",
        y="Facturas",
        text="Facturas",
        labels={"Fecha": "Mes", "Facturas": "Facturas únicas"},
        title="Cantidad de facturas por mes",
        color_discrete_sequence=["coral"],
    )
    fig_fact_mens.update_traces(textposition="outside")
    st.plotly_chart(fig_fact_mens, width="stretch")

    st.divider()
    st.subheader("Top productos más vendidos por mes")
    years = sorted(df_fact["AÑO"].unique())
    year_sel = st.selectbox("Año", years, index=len(years) - 1)
    mes_sel_nombre = st.selectbox(
        "Mes",
        [
            MES_NOMBRES[m]
            for m in sorted(
                df_fact[df_fact["AÑO"] == year_sel]["MES"].unique()
            )
        ],
    )
    mes_sel = next(k for k, v in MES_NOMBRES.items() if v == mes_sel_nombre)

    df_mes_sel = df_fact[
        (df_fact["AÑO"] == year_sel) & (df_fact["MES"] == mes_sel)
    ]
    top_mes = (
        df_mes_sel.groupby("item_name")
        .agg(
            Revenue=("total_product", "sum"),
            Unidades=("quantity", "sum"),
        )
        .reset_index()
        .nlargest(15, "Revenue")
    )
    if top_mes.empty:
        st.info("Sin datos para el período seleccionado.")
    else:
        fig_top_mes = px.bar(
            top_mes,
            x="Revenue",
            y="item_name",
            orientation="h",
            text=top_mes["Revenue"].apply(lambda v: f"${v:,.0f}"),
            labels={"Revenue": "Revenue (COP)", "item_name": ""},
            title=f"Top 15 productos — {mes_sel_nombre} {year_sel}",
        )
        fig_top_mes.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=660,
        )
        st.plotly_chart(fig_top_mes, width="stretch")

# ── Tab 5: Análisis avanzado ─────────────────────────────────────────────────
with tab5:
    # ── Pareto 80/20 ─────────────────────────────────────────────────────────
    st.subheader("Curva de Pareto — concentración de revenue")
    st.caption("¿Qué porcentaje de productos genera el 80% del revenue total?")

    df_pareto = (
        df_con_ventas[["name", "total_revenue"]]
        .sort_values("total_revenue", ascending=False)
        .copy()
        .reset_index(drop=True)
    )
    df_pareto["pct_productos"] = (df_pareto.index + 1) / len(df_pareto) * 100
    df_pareto["rev_acum"] = df_pareto["total_revenue"].cumsum()
    df_pareto["pct_revenue"] = (
        df_pareto["rev_acum"] / df_pareto["total_revenue"].sum() * 100
    )

    corte_80 = df_pareto[df_pareto["pct_revenue"] >= 80].iloc[0]
    pct_prod_80 = corte_80["pct_productos"]

    fig_pareto = go.Figure()
    fig_pareto.add_trace(
        go.Scatter(
            x=df_pareto["pct_productos"],
            y=df_pareto["pct_revenue"],
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
        x=pct_prod_80,
        line_dash="dash",
        line_color="coral",
        annotation_text=f"{pct_prod_80:.1f}% productos",
        annotation_position="top right",
    )
    fig_pareto.update_layout(
        xaxis_title="% de productos (ordenados por revenue desc.)",
        yaxis_title="% revenue acumulado",
        height=420,
    )
    st.plotly_chart(fig_pareto, width="stretch")
    st.caption(
        f"El {pct_prod_80:.1f}% de los productos ({int(round(pct_prod_80 / 100 * len(df_pareto)))} "
        f"de {len(df_pareto)}) concentra el 80% del revenue total."
    )

    st.divider()

    # ── Precio real de venta vs precio catálogo ──────────────────────────────
    st.subheader("Precio real de venta vs precio catálogo")
    st.caption(
        "Precio real = revenue total / unidades vendidas. "
        "Una diferencia negativa indica descuentos o variaciones de precio."
    )

    df_precio_real = df_con_ventas[
        df_con_ventas["total_sold_quantity"] > 0
    ].copy()
    df_precio_real["precio_real"] = (
        df_precio_real["total_revenue"] / df_precio_real["total_sold_quantity"]
    )
    df_precio_real["diff_pct"] = (
        (df_precio_real["precio_real"] - df_precio_real["price"])
        / df_precio_real["price"].replace(0, float("nan"))
        * 100
    )

    col_pr1, col_pr2 = st.columns(2)
    with col_pr1:
        fig_scatter_precio = px.scatter(
            df_precio_real,
            x="price",
            y="precio_real",
            hover_data=["name"],
            labels={
                "price": "Precio catálogo (COP)",
                "precio_real": "Precio real vendido (COP)",
            },
            title="Catálogo vs precio real",
            opacity=0.6,
        )
        p_max = df_precio_real[["price", "precio_real"]].max().max()
        fig_scatter_precio.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=p_max,
            y1=p_max,
            line={"color": "firebrick", "dash": "dash"},
        )
        st.plotly_chart(fig_scatter_precio, width="stretch")
        st.caption("La línea roja representa precio real = precio catálogo.")

    with col_pr2:
        diff_clip = df_precio_real["diff_pct"].clip(-100, 100)
        fig_diff = px.histogram(
            diff_clip,
            nbins=40,
            labels={"value": "Diferencia %"},
            title="Distribución de diferencia precio real vs catálogo",
        )
        fig_diff.update_layout(bargap=0.05)
        st.plotly_chart(fig_diff, width="stretch")
        mediana_diff = df_precio_real["diff_pct"].median()
        st.caption(
            f"Mediana de diferencia: {mediana_diff:+.1f}%. "
            "Valores negativos = vendido por debajo del catálogo."
        )

    st.divider()

    # ── Frecuencia en facturas ───────────────────────────────────────────────
    st.subheader("Frecuencia de aparición en facturas")
    st.caption(
        "Cuántas facturas distintas incluyen cada producto. "
        "Alta frecuencia = producto de alta rotación / arrastre."
    )

    freq_fact = (
        df_fact.groupby("item_id")["id"]
        .nunique()
        .reset_index()
        .rename(columns={"id": "n_facturas", "item_id": "id"})
    )
    df_freq = df_prod[["id", "name", "total_revenue", "price"]].merge(
        freq_fact, on="id", how="left"
    )
    df_freq["n_facturas"] = df_freq["n_facturas"].fillna(0).astype(int)

    top_freq = df_freq.nlargest(20, "n_facturas")
    fig_freq = px.bar(
        top_freq,
        x="n_facturas",
        y="name",
        orientation="h",
        text="n_facturas",
        labels={"n_facturas": "Facturas únicas", "name": ""},
        title="Top 20 productos por frecuencia en facturas",
    )
    fig_freq.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=700,
    )
    st.plotly_chart(fig_freq, width="stretch")

    st.divider()

    # ── Scatter precio vs revenue ────────────────────────────────────────────
    st.subheader("Precio unitario vs revenue total")
    st.caption(
        "Revela si los productos más caros son los que más venden, "
        "o si el volumen proviene de productos de bajo precio."
    )

    fig_pxr = px.scatter(
        df_con_ventas,
        x="price",
        y="total_revenue",
        size="total_sold_quantity",
        hover_data=["name", "total_sold_quantity"],
        labels={
            "price": "Precio unitario (COP)",
            "total_revenue": "Revenue total (COP)",
            "total_sold_quantity": "Unidades",
        },
        title="Precio vs revenue (tamaño = unidades vendidas)",
        opacity=0.65,
    )
    st.plotly_chart(fig_pxr, width="stretch")

    st.divider()

    # ── Rotación de inventario ───────────────────────────────────────────────
    st.subheader("Rotación de inventario")
    st.caption(
        "Rotación = unidades vendidas / stock disponible. "
        "Valores altos indican productos que se mueven rápido. "
        "Solo se muestran productos activos con stock > 0."
    )

    df_rot = df_activos[df_activos["available_quantity"] > 0].copy()
    df_rot["rotacion"] = (
        df_rot["total_sold_quantity"] / df_rot["available_quantity"]
    )

    top_rot = df_rot.nlargest(20, "rotacion")[
        ["name", "rotacion", "total_sold_quantity", "available_quantity"]
    ]
    fig_rot = px.bar(
        top_rot,
        x="rotacion",
        y="name",
        orientation="h",
        text=top_rot["rotacion"].apply(lambda v: f"{v:.1f}x"),
        labels={"rotacion": "Rotación (vendido/stock)", "name": ""},
        title="Top 20 productos por rotación de inventario",
    )
    fig_rot.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=800,
    )
    st.plotly_chart(fig_rot, width="stretch")

    st.divider()

    # ── Salud del catálogo ───────────────────────────────────────────────────
    st.subheader("Salud del catálogo")

    st.markdown("**Productos activos sin ninguna venta**")
    df_activos_sin_venta = df_activos[df_activos["total_revenue"] == 0][
        ["name", "price", "available_quantity"]
    ].copy()
    df_activos_sin_venta = df_activos_sin_venta.sort_values(
        "price", ascending=False
    )
    df_activos_sin_venta.columns = ["Producto", "Precio", "Stock"]
    df_activos_sin_venta["Precio"] = df_activos_sin_venta["Precio"].apply(
        lambda v: f"${v:,.0f}"
    )
    st.caption(
        f"{len(df_activos_sin_venta)} productos activos sin ventas registradas."
    )
    st.dataframe(df_activos_sin_venta, hide_index=True, width="stretch")

    st.markdown("**Productos inactivos con ventas registradas**")
    df_inact_con_venta = df_prod[
        (df_prod["status"] == "inactive") & (df_prod["total_revenue"] > 0)
    ][["name", "price", "total_sold_quantity", "total_revenue"]].copy()
    df_inact_con_venta = df_inact_con_venta.sort_values(
        "total_revenue", ascending=False
    )
    df_inact_con_venta.columns = [
        "Producto",
        "Precio",
        "Unidades vendidas",
        "Revenue",
    ]
    df_inact_con_venta["Precio"] = df_inact_con_venta["Precio"].apply(
        lambda v: f"${v:,.0f}"
    )
    df_inact_con_venta["Revenue"] = df_inact_con_venta["Revenue"].apply(
        lambda v: f"${v:,.0f}"
    )
    st.caption(
        f"{len(df_inact_con_venta)} productos inactivos que tienen ventas registradas."
    )
    st.dataframe(df_inact_con_venta, hide_index=True, width="stretch")
