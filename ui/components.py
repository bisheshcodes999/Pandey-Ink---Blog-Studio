"""Small reusable render bits shared by every panel - badges, cards,
section labels, empty states. Nothing here holds state or calls the
backend, just "given some text, spit out some HTML" helpers.
"""
from __future__ import annotations

from typing import Iterable, Optional

import streamlit as st

from ui.icons import icon as _icon


def badge(text: str, *, tone: str = "accent", icon: Optional[str] = None, mono: bool = False) -> str:
    """Returns the HTML for one pill badge (doesn't render it itself)."""
    tone_class = {"accent": "", "muted": "muted", "success": "success"}.get(tone, "")
    classes = " ".join(c for c in ["bwa-pill", tone_class, "mono" if mono else ""] if c)
    icon_html = f'{_icon(icon)}' if icon else ""
    return f'<span class="{classes}">{icon_html}{text}</span>'


def badges(items: Iterable[str]) -> None:
    """Renders a wrapping row of already-built badge HTML strings."""
    st.markdown(f'<div>{"".join(items)}</div>', unsafe_allow_html=True)


def section_label(text: str, icon: Optional[str] = None) -> None:
    icon_html = _icon(icon) if icon else ""
    st.markdown(
        f'<div class="bwa-section-label">{icon_html}<span>{text}</span></div>',
        unsafe_allow_html=True,
    )


def card_open(title: Optional[str] = None, icon: Optional[str] = None, flat: bool = False) -> None:
    """Opens a styled card div. Needs a matching card_close() call,
    with normal Streamlit widgets/markdown in between."""
    css_class = "bwa-card-flat" if flat else "bwa-card"
    header = ""
    if title:
        icon_html = _icon(icon) if icon else ""
        header = f'<div class="bwa-card-title">{icon_html}<span>{title}</span></div>'
    st.markdown(f'<div class="{css_class}">{header}', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def empty_state(title: str, description: str, icon: str = "inbox", small: bool = False) -> None:
    size_class = " small" if small else ""
    st.markdown(
        f'''<div class="bwa-empty{size_class}">
            <div class="bwa-empty-icon">{_icon(icon)}</div>
            <div class="bwa-empty-title">{title}</div>
            <div class="bwa-empty-desc">{description}</div>
        </div>''',
        unsafe_allow_html=True,
    )
