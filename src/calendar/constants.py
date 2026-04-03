"""Constantes del pipeline Google Calendar."""

from __future__ import annotations

FIELDS_TO_DROP: frozenset[str] = frozenset(
    {
        "kind",
        "etag",
        "htmlLink",
        "creator",
        "organizer",
        "iCalUID",
        "reminders",
        "eventType",
        "sequence",
        "originalStartTime",
        "recurringEventId",
        "attendees",
        "guestsCanInviteOthers",
        "privateCopy",
        "confirmed",
    }
)

COLOR_MAP: dict[str, str] = {
    "0": "Cliente asistió (default)",
    "1": "Cliente asistió (Lila)",
    "2": "Cliente falta y aviso (verde)",
    "3": "Pagos (morado)",
    "4": "Bonos / Regalos a clientes (rosado)",
    "5": "Cliente falta y no avisó (amarillo)",
    "6": "Evento en tienda / Ausencia trabajador / Festivo (rojo)",
    "8": "Por confirmar (negro)",
    "9": "Cita ya pagada (mes) (azul oscuro)",
    "10": "Cliente falta y aviso (verde)",
    "11": "Evento en tienda (rojo oscuro)",
}

EVENTS_COLS: list[str] = [
    "id",
    "summary",
    "description",
    "color_label",
    "recurrent_id",
    "color_id",
    "start",
    "end",
    "created",
    "updated",
]
