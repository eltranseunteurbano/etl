"""Extracción de datos desde la API REST de Alegra.

Obtiene facturas, productos y categorías en paralelo (paginación)
y los persiste como JSON en data/raw/alegra/.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import requests

from src.config.settings import (
    ALEGRA_BASE_URL,
    ALEGRA_EMAIL,
    ALEGRA_RAW_DIR,
    ALEGRA_TOKEN,
    ROOT,
    STATE_FILE,
)

_PAGE_SIZE = 30

_EXTRACT_PCT_LO = 12
_EXTRACT_PCT_HI = 44
_EXTRACT_SPAN = _EXTRACT_PCT_HI - _EXTRACT_PCT_LO


@dataclass
class _StreamState:
    fetched: int = 0
    total: int | None = None
    pages: int = 0
    done: bool = False


@dataclass
class _Streams:
    facturas: _StreamState = field(default_factory=_StreamState)
    productos: _StreamState = field(default_factory=_StreamState)
    categorias: _StreamState = field(default_factory=_StreamState)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _build_session() -> requests.Session:
    session = requests.Session()
    session.auth = (ALEGRA_EMAIL, ALEGRA_TOKEN)
    session.headers.update({"Accept": "application/json"})
    return session


def _coerce_total(v: object) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and v >= 0:
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


def _parse_total(payload: object) -> int | None:
    """Lee el total de registros desde ``metadata`` (API Alegra).

    Hay que enviar ``metadata=true`` en la query para que la respuesta
    incluya ``metadata`` con el total. Algunas respuestas anidan
    ``metadata.metadata.total`` (documentación OpenAPI).
    """
    if not isinstance(payload, dict):
        return None

    meta = payload.get("metadata")
    if isinstance(meta, dict):
        for key in ("total", "count", "totalCount"):
            t = _coerce_total(meta.get(key))
            if t is not None:
                return t
        inner = meta.get("metadata")
        if isinstance(inner, dict):
            for key in ("total", "count", "totalCount"):
                t = _coerce_total(inner.get(key))
                if t is not None:
                    return t

    for key in ("total", "count"):
        t = _coerce_total(payload.get(key))
        if t is not None:
            return t
    return None


def _stream_pct(st: _StreamState) -> float:
    if st.done:
        return 100.0
    if st.total and st.total > 0:
        return min(99.0, 100.0 * st.fetched / st.total)
    if st.pages == 0:
        return 0.0
    return min(95.0, 15.0 * st.pages)


def _detail_line(streams: _Streams) -> str:
    parts: list[str] = []

    def one(label: str, st: _StreamState) -> str:
        if st.done:
            tot = st.total if st.total is not None else st.fetched
            return f"{label} {st.fetched}/{tot} ✓"
        tot_s = str(st.total) if st.total is not None else "?"
        extra = ""
        if st.total is not None and st.fetched < st.total:
            extra = f" (~{st.total - st.fetched} pend.)"
        elif st.total is None and st.fetched > 0:
            extra = " (sin total API)"
        return f"{label} {st.fetched}/{tot_s}{extra}"

    parts.append(one("facturas", streams.facturas))
    parts.append(one("productos", streams.productos))
    parts.append(one("categorías", streams.categorias))
    return " · ".join(parts)


def _fetch_all(
    endpoint: str,
    params: dict | None,
    session: requests.Session,
    streams: _Streams,
    stream_key: str,
    on_emit: Callable[[], None],
) -> list[dict]:
    url = f"{ALEGRA_BASE_URL}{endpoint}"
    # Sin esto la API no devuelve metadata con el total (ver docs Alegra).
    base_params = {
        **(params or {}),
        "limit": _PAGE_SIZE,
        "metadata": "true",
    }

    results: list[dict] = []
    start = 0
    st_attr: _StreamState = getattr(streams, stream_key)

    while True:
        resp = session.get(
            url, params={**base_params, "start": start}, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()

        if isinstance(payload, dict):
            page = list(payload.get("data", []))
        else:
            page = list(payload)
        results.extend(page)

        total = _parse_total(payload)
        with streams.lock:
            st_attr.fetched = len(results)
            st_attr.pages += 1
            if total is not None:
                st_attr.total = total
        on_emit()

        if len(page) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE

    with streams.lock:
        st_attr.done = True
        st_attr.fetched = len(results)
    on_emit()

    return results


def _read_state() -> str | None:
    if not STATE_FILE.exists():
        return None
    with open(STATE_FILE, encoding="utf-8") as f:
        state: dict = json.load(f)
    return state.get("alegra", {}).get("last_invoice_date")


def _save_json(data: list[dict], filename: str) -> None:
    ALEGRA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = ALEGRA_RAW_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _job_facturas(
    streams: _Streams,
    params: dict,
    emit: Callable[[], None],
) -> tuple[str, list[dict]]:
    session = _build_session()
    data = _fetch_all("/invoices", params, session, streams, "facturas", emit)
    return ("facturas", data)


def _job_productos(
    streams: _Streams,
    emit: Callable[[], None],
) -> tuple[str, list[dict]]:
    session = _build_session()
    data = _fetch_all("/items", None, session, streams, "productos", emit)
    return ("productos", data)


def _job_categorias(
    streams: _Streams,
    emit: Callable[[], None],
) -> tuple[str, list[dict]]:
    session = _build_session()
    data = _fetch_all(
        "/categories", None, session, streams, "categorias", emit
    )
    return ("categorias", data)


def extract(
    *,
    on_progress: Callable[[int, str], None] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> None:
    """Descarga facturas, productos y categorías en paralelo."""

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)
        else:
            print(msg)

    if not (ALEGRA_EMAIL.strip() and ALEGRA_TOKEN.strip()):
        raise ValueError(
            "Alegra: define ALEGRA_EMAIL y ALEGRA_TOKEN en "
            f"{ROOT / '.env'}"
        )

    from_date = _read_state()

    if from_date:
        log(f"  Alegra: fetch incremental desde {from_date}\n")
        factura_params: dict = {"date_afterOrNow": from_date}
    else:
        log("  Alegra: fetch completo (primera ejecución)\n")
        factura_params = {}

    productos_path = ALEGRA_RAW_DIR / "productos.json"
    productos_ya_existen = productos_path.exists()

    streams = _Streams()
    if productos_ya_existen:
        with open(productos_path, encoding="utf-8") as f:
            productos_cached: list[dict] = json.load(f)
        streams.productos.fetched = len(productos_cached)
        streams.productos.total = len(productos_cached)
        streams.productos.done = True

    last_pct = [_EXTRACT_PCT_LO]

    def emit() -> None:
        if not on_progress:
            return
        with streams.lock:
            avg = (
                _stream_pct(streams.facturas)
                + _stream_pct(streams.productos)
                + _stream_pct(streams.categorias)
            ) / 3.0
            pct = _EXTRACT_PCT_LO + int(_EXTRACT_SPAN * avg / 100.0)
            pct = max(last_pct[0], min(_EXTRACT_PCT_HI, pct))
            last_pct[0] = pct
            detail = _detail_line(streams)
        on_progress(pct, detail)

    emit()

    futures = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_fact = pool.submit(_job_facturas, streams, factura_params, emit)
        f_cat = pool.submit(_job_categorias, streams, emit)
        futures = [f_fact, f_cat]
        if not productos_ya_existen:
            futures.append(pool.submit(_job_productos, streams, emit))

        out: dict[str, list[dict]] = {}
        for fut in as_completed(futures):
            key, data = fut.result()
            out[key] = data

    facturas_nuevas = out["facturas"]
    facturas_path = ALEGRA_RAW_DIR / "facturas.json"
    if from_date and facturas_path.exists():
        with open(facturas_path, encoding="utf-8") as f:
            facturas_previas: list[dict] = json.load(f)
        ids_nuevos = {inv["id"] for inv in facturas_nuevas}
        facturas = [
            inv for inv in facturas_previas if inv["id"] not in ids_nuevos
        ] + facturas_nuevas
    else:
        facturas = facturas_nuevas

    productos = productos_cached if productos_ya_existen else out["productos"]
    categorias = out["categorias"]

    _save_json(facturas, "facturas.json")
    log(f"  Alegra: {len(facturas)} facturas guardadas\n")
    if not productos_ya_existen:
        _save_json(productos, "productos.json")
        log(f"  Alegra: {len(productos)} productos guardados\n")
    else:
        log(
            f"  Alegra: productos ya existían "
            f"({len(productos)}), se omite fetch\n"
        )
    _save_json(categorias, "categorias.json")
    log(f"  Alegra: {len(categorias)} categorías guardadas\n")

    if on_progress:
        with streams.lock:
            detail = _detail_line(streams)
        on_progress(_EXTRACT_PCT_HI, detail)
