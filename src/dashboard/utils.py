"""Utils for the dashboard pages."""

from __future__ import annotations

import json

import streamlit as st

BRAND = "Srta. Eva"


def set_browser_tab_title(*suffix_parts: str) -> None:
    """Set the browser tab title."""
    label = " · ".join(suffix_parts)
    title = f"{BRAND} - {label}"
    st.html(
        f"<script>document.title = {json.dumps(title)};</script>",
        unsafe_allow_javascript=True,
    )
