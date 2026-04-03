"""Autenticación OAuth 2.0 para Google Calendar.

Lee el token cacheado (token.json) y lo refresca si es necesario.
Si no hay token, abre el flujo interactivo en el navegador.
"""

from __future__ import annotations

from google.auth.exceptions import RefreshError  # type: ignore[import]
from google.auth.transport.requests import Request  # type: ignore[import]
from google.oauth2.credentials import Credentials  # type: ignore[import]
from google_auth_oauthlib.flow import (  # type: ignore[import]
    InstalledAppFlow,
)

from src.config.settings import (
    GOOGLE_CLIENT_SECRETS_FILE,
    GOOGLE_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_credentials() -> Credentials:
    """Devuelve credenciales válidas, refrescando o re-autenticando."""
    creds: Credentials | None = None

    if GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(GOOGLE_TOKEN_FILE), SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_CLIENT_SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        GOOGLE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        GOOGLE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return creds
