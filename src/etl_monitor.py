"""Monitor de consola para ETL en paralelo (Rich + redirección de stdout)."""

from __future__ import annotations

import io
import logging
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_logger = logging.getLogger("etl")

WORKER_NAMES = frozenset({"ventas", "peluqueria", "alegra", "calendar"})


@dataclass
class LineState:
    label: str
    pct: int = 0
    phase: str = "iniciando…"
    done: bool = False
    done_msg: str = ""
    t0: float = field(default_factory=time.monotonic)


class EtlMonitor:
    """Estado por hilo + cola de logs para la vista Rich."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._lines: dict[str, LineState] = {
            "ventas": LineState("ventas"),
            "peluqueria": LineState("peluquería"),
            "alegra": LineState("alegra"),
            "calendar": LineState("calendar"),
        }
        self._log: deque[str] = deque(maxlen=200)
        self._buf: dict[str, str] = {k: "" for k in self._lines}

    def arm(self, key: str) -> None:
        with self._lock:
            st = self._lines[key]
            st.t0 = time.monotonic()
            st.done = False
            st.pct = 0
            st.phase = "iniciando…"
            st.done_msg = ""

    def set_phase(self, key: str, pct: int, phase: str) -> None:
        with self._lock:
            self._lines[key].pct = max(0, min(100, pct))
            self._lines[key].phase = phase

    def finish(
        self,
        key: str,
        *,
        rows: int | None = None,
        message: str = "",
    ) -> None:
        with self._lock:
            st = self._lines[key]
            st.done = True
            st.pct = 100
            elapsed = time.monotonic() - st.t0
            if message:
                st.done_msg = f"Completado {elapsed:.1f}s | {message}"
            elif rows is not None:
                st.done_msg = (
                    f"Completado {elapsed:.1f}s | {rows} filas en SQLite"
                )
            else:
                st.done_msg = (
                    f"Completado {elapsed:.1f}s | sin datos intermedios"
                )

    def flush_partial_line(self, thread_name: str) -> None:
        """Emite el buffer pendiente sin salto de línea al terminar."""
        with self._lock:
            buf = self._buf.get(thread_name, "")
            if buf.strip():
                prefix = f"[{thread_name}] "
                self._log.append(prefix + buf.rstrip())
            self._buf[thread_name] = ""

    def add_log(self, thread_name: str, s: str) -> None:
        with self._lock:
            prefix = f"[{thread_name}] "
            buf = self._buf.get(thread_name, "") + s
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.strip():
                    entry = prefix + line.rstrip("\r")
                    self._log.append(entry)
                    _logger.info("%s", entry)
            self._buf[thread_name] = buf

    def _elapsed(self, key: str) -> float:
        return time.monotonic() - self._lines[key].t0

    def render(self) -> Group:
        with self._lock:
            table = Table(show_header=False, box=None, padding=(0, 1))
            for key in ("ventas", "peluqueria", "alegra", "calendar"):
                st = self._lines[key]
                if st.done:
                    row = Text(f"Hilo {st.label} → {st.done_msg}")
                else:
                    e = self._elapsed(key)
                    row = Text(
                        f"Hilo {st.label} → {st.pct}%  {st.phase}  ·  {e:.1f}s"
                    )
                table.add_row(row)
            logs = "\n".join(self._log)
        body = Text(logs) if logs else Text("…", style="dim")
        log_panel = Panel(
            body,
            title="Logs (salida de cada hilo)",
            border_style="dim",
        )
        return Group(
            Panel(table, title="Estado por hilo", border_style="cyan"),
            log_panel,
        )


class WorkerStdout(io.TextIOBase):
    """Envía stdout de hilos conocidos al monitor; el resto al stdout real."""

    encoding = "utf-8"

    def __init__(self, monitor: EtlMonitor, real: io.TextIOBase) -> None:
        super().__init__()
        self._monitor = monitor
        self._real = real

    def write(self, s: str) -> int:
        if not s:
            return 0
        name = threading.current_thread().name
        if name in WORKER_NAMES:
            self._monitor.add_log(name, s)
            return len(s)
        self._real.write(s)
        return len(s)

    def flush(self) -> None:
        self._real.flush()

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return False


def _run_ventas(monitor: EtlMonitor) -> None:
    threading.current_thread().name = "ventas"
    monitor.arm("ventas")
    from src.ventas.extract import extract
    from src.ventas.load import load
    from src.ventas.transform import transform

    monitor.set_phase("ventas", 12, "extract")
    extract()
    monitor.set_phase("ventas", 44, "transform")
    transform()
    monitor.set_phase("ventas", 78, "load")
    rows = load()
    monitor.flush_partial_line("ventas")
    monitor.finish("ventas", rows=rows)


def _run_peluqueria(monitor: EtlMonitor) -> None:
    threading.current_thread().name = "peluqueria"
    monitor.arm("peluqueria")
    from src.peluqueria.extract import extract
    from src.peluqueria.load import load
    from src.peluqueria.transform import transform

    monitor.set_phase("peluqueria", 12, "extract")
    extract()
    monitor.set_phase("peluqueria", 44, "transform")
    transform()
    monitor.set_phase("peluqueria", 78, "load")
    rows = load()
    monitor.flush_partial_line("peluqueria")
    monitor.finish("peluqueria", rows=rows)


def _run_alegra(monitor: EtlMonitor) -> None:
    threading.current_thread().name = "alegra"
    monitor.arm("alegra")
    from src.alegra.extract import extract
    from src.alegra.load import load
    from src.alegra.transform import transform

    def progress(pct: int, detail: str) -> None:
        monitor.set_phase("alegra", pct, detail)

    def log(msg: str) -> None:
        monitor.add_log("alegra", msg)

    extract(on_progress=progress, on_log=log)
    monitor.set_phase("alegra", 44, "transform")
    transform()
    monitor.set_phase("alegra", 78, "load")
    msg = load()
    monitor.flush_partial_line("alegra")
    monitor.finish("alegra", message=msg)


def _run_calendar(monitor: EtlMonitor) -> None:
    threading.current_thread().name = "calendar"
    monitor.arm("calendar")
    from src.calendar.extract import extract
    from src.calendar.load import load
    from src.calendar.transform import transform

    def progress(pct: int, detail: str) -> None:
        monitor.set_phase("calendar", pct, detail)

    def log(msg: str) -> None:
        monitor.add_log("calendar", msg)

    extract(on_progress=progress, on_log=log)
    monitor.set_phase("calendar", 44, "transform")
    transform()
    monitor.set_phase("calendar", 78, "load")
    msg = load()
    monitor.flush_partial_line("calendar")
    monitor.finish("calendar", message=msg)


def run_etl_with_monitor() -> None:
    """Ejecuta los cuatro pipelines en paralelo con vista Rich."""
    monitor = EtlMonitor()
    old_stdout = sys.stdout
    sys.stdout = WorkerStdout(monitor, old_stdout)
    stop_event = threading.Event()
    console = Console(stderr=True)

    def tick(live: Live) -> None:
        while True:
            live.update(monitor.render())
            if stop_event.wait(0.08):
                break

    try:
        with Live(
            monitor.render(),
            console=console,
            refresh_per_second=12,
            transient=False,
        ) as live:
            ticker = threading.Thread(target=tick, args=(live,), daemon=True)
            ticker.start()
            try:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    fut_v = executor.submit(_run_ventas, monitor)
                    fut_p = executor.submit(_run_peluqueria, monitor)
                    fut_a = executor.submit(_run_alegra, monitor)
                    fut_c = executor.submit(_run_calendar, monitor)
                    failed: list[BaseException] = []
                    for fut in (fut_v, fut_p, fut_a, fut_c):
                        try:
                            fut.result()
                        except Exception as exc:
                            _logger.error(
                                "Pipeline falló: %s", exc, exc_info=True
                            )
                            failed.append(exc)
                    if failed:
                        raise failed[0]
            finally:
                stop_event.set()
                ticker.join(timeout=3)
                live.update(monitor.render())
    finally:
        sys.stdout = old_stdout
