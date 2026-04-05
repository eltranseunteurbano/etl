# ETL Srta. Eva

**Autores:**
- Anny Julieth Valencia Jaramillo
- Jaime David Burbano Montoya
- Nayla Ximena Ledesma Montano

Proyecto de **extracción, transformación y carga (ETL)** de datos operativos de una tienda de mascotas. Procesa ventas en Excel, registros de peluquería, contabilidad (Alegra) y citas (Google Calendar), los consolida en un **almacén SQLite** y los expone a través de un **dashboard analítico en Streamlit** con sección de predicciones y análisis estadístico.

---

## Contenido

- [Requisitos](#requisitos)
- [Configuración](#configuración)
  - [Google Calendar: archivos en `credentials/`](#google-calendar-archivos-en-credentials)
- [Cómo correr](#cómo-correr)
- [Arquitectura](#arquitectura)
- [Predicciones y análisis](#predicciones-y-análisis)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Requisitos

- **Python ≥ 3.11**
- **[uv](https://github.com/astral-sh/uv)** para gestión de dependencias

```bash
uv sync
```

---

## Configuración

Copia `.env.example` a `.env` y completa las credenciales necesarias:

```bash
cp .env.example .env
```

Variables relevantes:
- `ALEGRA_EMAIL` / `ALEGRA_TOKEN` — API de contabilidad Alegra
- `GOOGLE_CALENDAR_ID` — ID del calendario (suele ser tu correo de Google)
- `GOOGLE_CLIENT_SECRETS_FILE` / `GOOGLE_TOKEN_FILE` — rutas a los JSON de OAuth (por defecto bajo `credentials/`; solo hace falta definirlas si usas otra ubicación)
- `DASH_HOST` / `DASH_PORT` / `DASH_DEBUG` — servidor del dashboard

> Sin Alegra o Calendar configurados, esos pipelines no traerán datos; los pipelines de ventas y peluquería (basados en Excel) funcionan de forma independiente.

### Google Calendar: archivos en `credentials/`

El pipeline de Calendar **no funciona** hasta que existan estos archivos en el disco (no van en Git; están en `.gitignore` para no subir secretos a GitHub).

1. **`credentials/client_secrets.json`** — Debes **añadirlo tú manualmente**. Descárgalo desde [Google Cloud Console](https://console.cloud.google.com/) → *APIs y servicios* → *Credenciales* → cliente OAuth 2.0 (tipo *Escritorio* o el que uses para el flujo instalado). Coloca el JSON en `credentials/client_secrets.json` (o la ruta que indiques en `GOOGLE_CLIENT_SECRETS_FILE` dentro de `.env`).

2. **`credentials/token.json`** — No se entrega con el proyecto. Se **genera automáticamente** la primera vez que ejecutas el ETL de Calendar (o `src.calendar.pipeline`): se abrirá el navegador para autorizar la app y el token quedará guardado en ese archivo.

Más detalle y despliegue en servidor: [`credentials/README.md`](credentials/README.md).

---

## Cómo correr

### ETL y dashboard

```bash
uv run python main.py              # ETL completo + dashboard
uv run python main.py --etl        # Solo ETL
uv run python main.py --dash       # Solo dashboard
```

### Dashboard directo con Streamlit

```bash
uv run streamlit run src/dashboard/main.py
```

### Un pipeline por separado

```bash
uv run python -c "from src.ventas.pipeline import ventas_pipeline; ventas_pipeline()"
uv run python -c "from src.peluqueria.pipeline import peluqueria_pipeline; peluqueria_pipeline()"
uv run python -c "from src.alegra.pipeline import pipeline; pipeline()"
uv run python -c "from src.calendar.pipeline import pipeline; pipeline()"
```

### Pruebas y estilo (PEP 8)

```bash
uv run pytest
uv run flake8 src/
```

---

## Arquitectura

Cuatro pipelines ETL independientes bajo `src/`, ejecutados en paralelo por `src/etl_monitor.py` (`ThreadPoolExecutor` + monitor Rich en consola).

### Flujo de datos

**Ventas y peluquería** (basados en Excel):
```
data/sources/  →  extract()  →  data/raw/
                               ↓ transform()
                            data/interim/
                               ↓ load()
                            data/processed/  +  data/warehouse.sqlite
```

**Alegra y Calendar** (basados en API):
```
REST API / Google Calendar API
  →  extract()   →  data/raw/<pipeline>/
  →  transform() →  data/interim/<pipeline>/
  →  load()      →  data/warehouse.sqlite
```

### Módulos por pipeline

Cada uno sigue el mismo patrón:

| Archivo | Rol |
|---------|-----|
| `constants.py` | Nombres de columna y mapeos |
| `extract.py` | Fuente → CSV/JSON crudo |
| `transform.py` | Limpieza, normalización, validación |
| `load.py` | CSV procesado + tabla SQLite |
| `pipeline.py` | Orquesta extract → transform → load |

Las rutas compartidas están en `src/config/settings.py` (`ROOT`, `RAW_FOLDER`, `DATABASE_PATH`, etc.). Nunca las hardcodees.

### Dashboard

Aplicación multipágina en Streamlit con navegación por secciones:

- **Inicio** — resumen general
- **Tienda** — dashboard, ventas, productos
- **Peluquería** — dashboard, agenda, ventas
- **Análisis → Predicciones** — modelos estadísticos (ver sección siguiente)

---

## Predicciones y análisis

Accesible desde **Análisis → Predicciones** en el dashboard. Todo es estimación sobre datos históricos.

### Pestaña 1 — Forecast de ingresos

**Proyección mensual (Holt-Winters)**
- Modelo `ExponentialSmoothing` de statsmodels con tendencia aditiva y, si hay ≥ 18 meses de historia, estacionalidad anual (periodo 12).
- El usuario elige fuente: **tienda** (`VENTAS_POST`) o **peluquería** (`PELUQUERÍA`).
- Slider de horizonte (1–6 meses). Se muestran histórico, serie ajustada, proyección e intervalo al 95 % (basado en residuos).
- Requiere mínimo **6 meses** de datos; el mes en curso incompleto se excluye del ajuste.

**Ventas cerca de festivos colombianos**
- Usa `holidays.country_holidays("CO")`.
- Clasifica cada día como **normal**, **pre-festivo** (hasta 7 días antes) o **festivo**.
- Muestra mediana de ventas diarias por tipo de día y top 10 festivos con mayor mediana en víspera.

### Pestaña 2 — Riesgo de inasistencia

- **Datos**: citas del calendario etiquetadas como *asistió* / *faltó* (campo `color_label` en `calendar_events`).
- **Modelo**: regresión logística (scikit-learn) con variables hora, día de semana, mes, festivo y víspera de festivo. Predictores estandarizados con `StandardScaler`.
- **Salidas**:
  - métricas generales (citas, tasa de inasistencia, exactitud por validación cruzada);
  - mapa de calor día × hora con probabilidad estimada de inasistencia en escenario normal;
  - tasa de inasistencia por tipo de día (normal / pre-festivo / festivo);
  - importancia relativa de cada predictor (valor absoluto de coeficientes).
- Requiere mínimo **30 citas** etiquetadas.

---

## Estructura del proyecto

| Ruta | Rol |
|------|-----|
| `main.py` | Entrada: ETL y/o dashboard |
| `src/config/settings.py` | Rutas y constantes compartidas |
| `src/ventas/` | Pipeline ETL de ventas |
| `src/peluqueria/` | Pipeline ETL de peluquería |
| `src/alegra/` | Pipeline ETL de Alegra (API) |
| `src/calendar/` | Pipeline ETL de Google Calendar |
| `src/etl_monitor.py` | Ejecución paralela de los pipelines |
| `src/dashboard/main.py` | Entrada del dashboard Streamlit |
| `src/dashboard/pages/` | Páginas del dashboard (incl. `predicciones.py`) |
| `data/warehouse.sqlite` | Base analítica unificada |
| `data/state.json` | Estado incremental (Calendar, etc.) |
| `credentials/` | OAuth de Google Calendar: añadir `client_secrets.json`; `token.json` se crea al primer uso (no versionar) |
