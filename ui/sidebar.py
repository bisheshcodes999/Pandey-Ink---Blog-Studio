"""Left sidebar - brand lockup, the "generate a post" form, and the
saved posts list.

Only captures input and renders - doesn't touch st.session_state
itself (besides Streamlit's own widget state) and doesn't call the
backend. bwa_frontend.py reads the returned SidebarState and decides
what to do (run the pipeline, clear results, load a saved post).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from ui.components import card_close, card_open, section_label
from ui.icons import icon as _icon
from ui.saved_posts import build_label_map, list_past_blogs, relative_time

# Label -> internal value, gets threaded through to
# backend/nodes/orchestrator.py as desired_length/desired_tone. Keep
# these (and the _SUMMARY dicts below) in sync with backend/config.py's
# LENGTH_PRESETS - just display copies of the same numbers, kept here
# instead of imported so ui/ doesn't reach into backend/ directly.
_LENGTH_OPTIONS = {
    "Short (about 700 words)": "short",
    "Medium (about 1,400 words)": "medium",
    "Long (about 3,000 words)": "long",
}
_LENGTH_SUMMARY = {
    "short": "about 700 words across 3-4 sections",
    "medium": "about 1,400 words across 5-7 sections",
    "long": "about 3,000 words across 7-9 sections",
}
_TONE_OPTIONS = {
    "Auto (Model decides)": "",
    "Professional": "professional",
    "Casual / Conversational": "casual and conversational",
    "Funny / Witty": "funny and witty",
    "Beginner-Friendly": "beginner-friendly, simple language",
    "Technical / Expert": "technical and expert-level",
}
_TONE_SUMMARY = {
    "": "whatever tone best fits the topic",
    "professional": "a professional tone",
    "casual and conversational": "a casual, conversational tone",
    "funny and witty": "a funny, witty tone",
    "beginner-friendly, simple language": "simple, beginner-friendly language",
    "technical and expert-level": "a technical, expert-level tone",
}
# Same idea as _LENGTH_OPTIONS/_TONE_OPTIONS above -- kept in sync with
# backend/config.py's LANGUAGE_OPTIONS keys ("english"/"nepali").
_LANGUAGE_OPTIONS = {
    "English": "english",
    "Nepali (नेपाली)": "nepali",
}
_LANGUAGE_SUMMARY = {
    "english": "English",
    "nepali": "Nepali",
}

# Quick differentiator controls -- what actually makes a run here
# different from just asking a generic chatbot for a blog post: who
# it's written for, what shape it takes, whether it cites the research
# it pulled, and what an illustration should look like (or whether
# there should be one at all). Empty string == "auto, let the model
# decide" for the first two, same convention as Tone above. Kept in
# sync with backend/config.py's AUDIENCE_OPTIONS/STRUCTURE_OPTIONS/
# IMAGE_STYLE_OPTIONS keys.
_AUDIENCE_OPTIONS = {
    "Auto (let the model decide)": "",
    "Complete beginners": "beginners",
    "Practitioners / engineers": "practitioners",
    "Executives / decision-makers": "executives",
    "Students": "students",
}
_STRUCTURE_OPTIONS = {
    "Auto (let the model decide)": "",
    "Explainer": "explainer",
    "Tutorial / how-to": "tutorial",
    "Comparison (X vs Y)": "comparison",
    "News roundup": "news_roundup",
    "System design deep-dive": "system_design",
}
_CITATION_OPTIONS = {
    "Auto (based on research)": "auto",
    "Always cite sources": "always",
    "Never cite sources": "never",
}
_IMAGE_STYLE_OPTIONS = {
    "Auto (let the model decide)": "",
    "Technical diagram": "diagram",
    "Flat illustration": "flat",
    "Whiteboard sketch": "sketch",
    "Photorealistic": "photorealistic",
}

# Quick-pick starting points so the sidebar has something to click on
# right away instead of always needing to type a topic.
_EXAMPLE_TOPICS = ["Jay Nepal", "How does human learn to speak?", "The Roman Empire"]


@dataclass
class SidebarState:
    topic: str
    as_of: date
    length: str
    tone: str
    language: str
    audience: str
    blog_kind: str
    citation_mode: str
    include_images: bool
    image_style: str
    run_clicked: bool
    clear_clicked: bool
    load_clicked: bool
    selected_path: Optional[Path]
    past_files: List[Path]


def render_sidebar(
    *,
    app_name: str,
    model_name: str,
    topic_prefill: str,
    past_blogs_limit: int = 50,
) -> SidebarState:
    with st.sidebar:
        # ---- Brand ----
        st.markdown(
            f'''<div class="bwa-brand">
                <div class="bwa-brand-mark">{_icon("sparkles")}</div>
                <div class="bwa-brand-text">
                    <span class="bwa-brand-title">{app_name}</span>
                    <span class="bwa-brand-sub">AI based Blog Studio </span>
                </div>
            </div>''',
            unsafe_allow_html=True,
        )

        # ---- New post ----
        # Not an st.form on purpose - keeping Length/Tone as plain
        # widgets means changing either one reruns right away, so the
        # summary caption below always matches the current choice
        # instead of only updating after "Generate blog" is clicked.
        # Wrapped in its own container key so the motto-style title
        # ("Your thinking, drafted.") can be styled bigger/bolder/caps
        # in styles.py without touching every other card's title too.
        with st.container(key="bwa_new_blog_card"):
            card_open("Your thinking, drafted.", icon="lightbulb")

            st.markdown(
                '<div class="bwa-idea-prompt">Need an idea? Try one of these:</div>',
                unsafe_allow_html=True,
            )
            with st.container(key="bwa_topic_chips"):
                chip_cols = st.columns(len(_EXAMPLE_TOPICS))
                for chip_col, example in zip(chip_cols, _EXAMPLE_TOPICS):
                    if chip_col.button(example, width="stretch", key=f"bwa_example_{example}"):
                        st.session_state["topic_prefill"] = example
                        st.rerun()

            topic = st.text_area(
                "Topic",
                value=topic_prefill,
                height=100,
                placeholder="e.g. Vector databases for retrieval-augmented generation",
            )
            st.caption(
                "A specific, scoped topic produces a tighter outline than a single keyword.")

            length_col, tone_col = st.columns(2)
            length_label = length_col.selectbox(
                "Length", list(_LENGTH_OPTIONS.keys()), index=1)
            tone_label = tone_col.selectbox(
                "Tone", list(_TONE_OPTIONS.keys()), index=0)
            length_value = _LENGTH_OPTIONS[length_label]
            tone_value = _TONE_OPTIONS[tone_label]

            language_label = st.selectbox(
                "Language", list(_LANGUAGE_OPTIONS.keys()), index=0)
            language_value = _LANGUAGE_OPTIONS[language_label]

            st.caption(
                f"This post will run {_LENGTH_SUMMARY[length_value]}, in {_TONE_SUMMARY[tone_value]}, "
                f"written in {_LANGUAGE_SUMMARY[language_value]}."
            )

            # ---- Quick differentiator controls ----
            # What separates a run here from just asking a chatbot:
            # who it's for, what shape it takes, and whether sources
            # get cited -- all real levers on the actual multi-agent
            # pipeline, not just cosmetic.
            section_label("Make it yours", icon="sparkles")
            audience_col, structure_col = st.columns(2)
            audience_label = audience_col.selectbox(
                "Audience", list(_AUDIENCE_OPTIONS.keys()), index=0)
            structure_label = structure_col.selectbox(
                "Structure", list(_STRUCTURE_OPTIONS.keys()), index=0)
            audience_value = _AUDIENCE_OPTIONS[audience_label]
            blog_kind_value = _STRUCTURE_OPTIONS[structure_label]

            citation_label = st.selectbox(
                "Citations", list(_CITATION_OPTIONS.keys()), index=0)
            citation_mode_value = _CITATION_OPTIONS[citation_label]

            include_images = st.checkbox("Include images", value=True)
            if include_images:
                image_style_label = st.selectbox(
                    "Image style", list(_IMAGE_STYLE_OPTIONS.keys()), index=0)
                image_style_value = _IMAGE_STYLE_OPTIONS[image_style_label]
            else:
                image_style_value = ""
                st.caption("This post will skip illustrations entirely.")

            as_of = st.date_input("Facts as of", value=date.today())
            run_clicked = st.button(
                "Generate blog", type="primary", width="stretch")

            card_close()

        # Session/model badge intentionally removed from view per request -
        # model_name is still accepted above for callers that want it, just
        # not rendered here anymore. Clear results sits right under the
        # New Blog card with nothing else between them.
        clear_clicked = st.button("Clear results", width="stretch")

        st.divider()

        # ---- Saved posts ----
        section_label("Saved blogs", icon="folder-open")
        past_files = list_past_blogs()

        selected_path: Optional[Path] = None
        load_clicked = False

        if not past_files:
            st.caption("Generated posts will appear here.")
        else:
            visible = past_files[:past_blogs_limit]
            file_by_label: Dict[str, Path] = build_label_map(visible)
            labels = list(file_by_label.keys())

            selected_label = st.selectbox(
                "Select a post to reopen", options=labels, label_visibility="collapsed"
            )
            selected_path = file_by_label[selected_label]
            try:
                mtime = selected_path.stat().st_mtime
                st.caption(f"Last updated {relative_time(mtime)}")
            except OSError:
                pass
            load_clicked = st.button("Load selected post", width="stretch")

    return SidebarState(
        topic=topic,
        as_of=as_of,
        length=length_value,
        tone=tone_value,
        language=language_value,
        audience=audience_value,
        blog_kind=blog_kind_value,
        citation_mode=citation_mode_value,
        include_images=include_images,
        image_style=image_style_value,
        run_clicked=run_clicked,
        clear_clicked=clear_clicked,
        load_clicked=load_clicked,
        selected_path=selected_path,
        past_files=past_files,
    )
