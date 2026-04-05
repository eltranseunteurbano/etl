# Credenciales Google Calendar (local)

Estos archivos **no deben subirse a Git** (GitHub los bloquea y exponen tu cuenta).

| Archivo | Origen |
|---------|--------|
| `client_secrets.json` | Descárgalo desde [Google Cloud Console](https://console.cloud.google.com/) → APIs y servicios → Credenciales → OAuth 2.0. |
| `token.json` | Se genera la **primera vez** que ejecutas el ETL de Calendar en tu máquina (flujo de login en el navegador). |

## En tu PC

1. Coloca `client_secrets.json` en esta carpeta (`credentials/`).
2. Ejecuta el ETL; al pedir Calendar, completa OAuth; se creará `token.json` aquí.
3. Haz `git status`: no debe listar `token.json` ni `client_secrets.json` (están en `.gitignore`).

## En un servidor (Render, VPS, etc.)

No copies el repo con esos archivos. Usa **Secret Files** o variables del proveedor y monta las rutas que indiques en `.env` (`GOOGLE_CLIENT_SECRETS_FILE`, `GOOGLE_TOKEN_FILE`).

## Si necesitas “subir” algo al equipo

Usa un canal seguro (1Password, Bitwarden, carpeta compartida cifrada, **no** el historial de Git).
