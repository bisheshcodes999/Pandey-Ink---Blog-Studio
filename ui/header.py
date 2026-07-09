"""Main content header - app name, tagline, and a row of status badges
(model, mode, etc.). Purely presentational.
"""
from __future__ import annotations

from typing import Iterable, Optional

import streamlit as st

from ui.components import badge


def render_header(
    app_name: str,
    tagline: str,
    *,
    model_name: Optional[str] = None,
    extra_badges: Iterable[str] = (),
) -> None:
    right_badges = []
    if model_name:
        right_badges.append(badge(f"Model in use: {model_name}", tone="muted", icon="cpu"))
    right_badges.extend(extra_badges)

    # "PandeyInk - Blog Studio" -> the brand ("PandeyInk") in accent
    # blue, the rest of the title in the default text color, instead of
    # one flat-colored string. Falls back to plain text if app_name
    # doesn't have the " - " separator this splits on.
    if " - " in app_name:
        brand, _, rest = app_name.partition(" - ")
        title_html = f'<span class="bwa-title-accent">{brand}</span> - {rest}'
    else:
        title_html = app_name

    st.markdown(
        f'''<div class="bwa-header">
            <div class="bwa-header-left">
                <h1>{title_html}</h1>
                <p>{tagline}</p>
            </div>
            <div class="bwa-header-badges">{"".join(right_badges)}</div>
        </div>''',
        unsafe_allow_html=True,
    )
