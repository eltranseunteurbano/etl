# ETL Tienda de Mascotas

Proyecto de **extracción, transformación y carga (ETL)** de datos operativos de una tienda de mascotas (ventas en Excel, peluquería, contabilidad Alegra y Google Calendar), con **almacén en SQLite** y **dashboard analítico** en Streamlit. Incluye una sección de **predicciones y análisis estadístico** sobre ingresos, patrones pre-festivos y riesgo de inasistencia a citas de peluquería.

---

## Qué se hizo

- **Cuatro pipelines ETL independientes** bajo `src/`: **ventas** y **peluquería** (Excel → CSV intermedios → tabla `ventas` en SQLite); **alegra** (API → raw/interim → SQLite); **calendar** (Google Calendar → eventos en SQLite). Se ejecutan en paralelo con un monitor de consola (`src/etl_monitor.py`).
- **Base de datos única** `data/warehouse.sqlite` como destino común de todas las cargas.
- **Dashboard multipágina** (`src/dashboard/main.py`) con navegación por secciones: inicio, Tienda (dashboard, ventas, productos), Peluquería (dashboard, agenda, ventas) y **Análisis → Predicciones**.
- **Página Predicciones** (`src/dashboard/pages/predicciones.py`): modelos de series de tiempo y regresión logística, más comparativas de ventas alrededor de **festivos colombianos** (librería `holidays`).

Los datos de negocio y nombres de columnas están en **español**, alineados con las fuentes originales.

---

## Cómo funciona (visión general)

1. **Fuentes**: archivos Excel en `data/sources/`, API de Alegra y API de Google Calendar (credenciales vía `.env`).
2. **ETL**: cada pipeline sigue el patrón **extract → transform → load**; las rutas centralizadas están en `src/config/settings.py` (`ROOT`, `RAW_FOLDER`, `DATABASE_PATH`, etc.).
3. **Carga**: tablas como `ventas`, `calendar_events` y las de Alegra quedan en `data/warehouse.sqlite`.
4. **Dashboard**: Streamlit lee la base al vuelo; Plotly se usa para gráficos interactivos.
5. **Estado incremental**: `data/state.json` ayuda a no reprocesar todo en cada corrida (según el diseño de cada pipeline).

---

## Requisitos

- **Python ≥ 3.11**
- **[uv](https://github.com/astral-sh/uv)** recomendado para dependencias (o un venv con las dependencias de `pyproject.toml`).

---

## Cómo se corre

Desde la raíz del repositorio (`etl/`):

```bash
uv sync
```

### ETL y dashboard

```bash
uv run python main.py              # ETL completo + arranque del dashboard
uv run python main.py --etl        # Solo ETL
uv run python main.py --dash       # Solo dashboard (sin ETL)
```

### Solo dashboard (equivalente directo con Streamlit)

```bash
uv run streamlit run src/dashboard/main.py
```

### Un pipeline suelto (ejemplos)

```bash
uv run python -c "from src.ventas.pipeline import ventas_pipeline; ventas_pipeline()"
uv run python -c "from src.peluqueria.pipeline import peluqueria_pipeline; peluqueria_pipeline()"
uv run python -c "from src.alegra.pipeline import pipeline; pipeline()"
uv run python -c "from src.calendar.pipeline import pipeline; pipeline()"
```

### Pruebas y calidad de código

```bash
uv run pytest
```

### Configuración

Copia `.env.example` a `.env` y completa credenciales donde aplique (Alegra, Google OAuth para Calendar, host/puerto del dashboard, etc.). Sin Calendar o Alegra configurados, esos pipelines pueden fallar o no traer datos; el resto del proyecto puede seguir siendo útil según lo que tengas en `data/`.

---

## Predicciones y análisis (`Análisis` → `Predicciones`)

La página tiene **dos pestañas**. Todo es **estimación** sobre datos históricos, no una garantía de resultados futuros.

### Pestaña 1 — Forecast de ingresos

1. **Proyección mensual (Holt-Winters)**
   - **Statsmodels** `ExponentialSmoothing`: tendencia aditiva y, si hay **al menos 18 meses** de historia, **estacionalidad anual** (periodo 12).
   - El usuario elige fuente: **tienda** (`VENTAS_POST`) o **peluquería** (`PELUQUERÍA`).
   - Slider de **horizonte** (1–6 meses). Se muestran histórico, serie ajustada, proyección e intervalo aproximado al 95 % (basado en dispersión de residuos).
   - Requisito mínimo: **6 meses** de datos agregados; si el último mes es el mes en curso incompleto, se excluye del ajuste.

2. **Ventas y días previos a festivo**
   - Usa **festivos de Colombia** (`holidays.country_holidays("CO")`).
   - Marca cada día de ventas como **normal**, **pre-festivo** (hasta **7 días** antes de un festivo) o **festivo**.
   - Gráficos de **mediana de ventas diarias** por tipo de día y **top 10 festivos** asociados a mayores medianas en víspera.

### Pestaña 2 — Riesgo de inasistencia

- **Datos**: citas del calendario con etiquetas de **asistió** vs **faltó** (según `color_label` en `calendar_events`).
- **Modelo**: **regresión logística** (scikit-learn), con variables **hora**, **día de semana**, **mes**, **día festivo** y **víspera de festivo** (misma ventana de 7 días). Los predictores se estandarizan con `StandardScaler`.
- **Salidas**:
  - métricas (citas, tasa de inasistencias, exactitud por validación cruzada, conteos pre-festivo/festivo);
  - **mapa de calor** día × hora con probabilidad estimada de inasistencia en escenario “día normal, sin festivo”;
  - barras de **tasa de inasistencia** por tipo de día (normal / pre-festivo / festivo);
  - barras de **importancia relativa** (valor absoluto de coeficientes del modelo).
- Requisito mínimo: **30 citas** etiquetadas en esas categorías.

---

## Estructura relevante

| Ruta | Rol |
|------|-----|
| `main.py` | Entrada: ETL y/o dashboard |
| `src/config/settings.py` | Rutas y constantes compartidas |
| `src/ventas/`, `src/peluqueria/`, `src/alegra/`, `src/calendar/` | Pipelines ETL |
| `src/etl_monitor.py` | Ejecución en paralelo del ETL |
| `src/dashboard/main.py` | Navegación Streamlit |
| `src/dashboard/pages/` | Páginas del dashboard (incl. `predicciones.py`) |
| `data/warehouse.sqlite` | Base analítica |
| `data/state.json` | Estado incremental (Calendar, etc.) |
