"""Main-page "Revise a draft" panel - upload your own draft + tell the
model what to change about it.

Lives on the main page, not the sidebar - it's a distinct starting
action (bring your own draft) alongside "Generate blog" in the
sidebar, not a sidebar setting, so it gets its own card up top where
you'd naturally look for it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import streamlit as st

from ui.components import card_close, card_open


@dataclass
class RevisePanelState:
    uploaded_draft: Optional[Any]
    edit_instruction: str
    revise_clicked: bool


def render_revise_panel() -> RevisePanelState:
    # Wrapped in its own container key so the card title can be sized
    # up in styles.py without also bumping every other card's title.
    with st.container(key="bwa_revise_card"):
        card_open("Revise a draft")
        st.caption("Bring your own draft and tell the model what to change.")

        uploaded_draft = st.file_uploader(
            "Upload a draft",
            type=["md", "txt", "docx"],
            label_visibility="collapsed",
        )
        edit_instruction = st.text_area(
            "What do you want changed?",
            height=80,
            placeholder="e.g. Make the tone more casual, add a conclusion, shorten the intro",
            label_visibility="collapsed",
        )
        revise_clicked = st.button("Revise draft", width="stretch")
        card_close()

    return RevisePanelState(
        uploaded_draft=uploaded_draft,
        edit_instruction=edit_instruction,
        revise_clicked=revise_clicked,
    )
