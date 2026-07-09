"""Env vars + tunable constants for the backend.

Keeping these in one place so a value like "3 images max" or the image
model name only lives in one spot instead of being copy-pasted wherever
it's needed.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ---- LLM ----
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# ---- Research (Tavily) ----
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MAX_RESEARCH_QUERIES = 10
MAX_RESULTS_PER_QUERY = 6
MAX_EVIDENCE_FOR_PLANNING_PROMPT = 16
MAX_EVIDENCE_FOR_WORKER_PROMPT = 20
MAX_EVIDENCE_FOR_FACT_CHECK = 20

# ---- Outline planning ----
# qwen3:8b doesn't always follow a numeric instruction like "5-9 tasks"
# in the orchestrator prompt, so orchestrator_node re-asks (up to
# MAX_PLAN_RETRIES times) instead of just accepting a 1-section outline.
# MIN_PLAN_TASKS is the fallback when no length preset matches (same as
# the "medium" preset below).
MIN_PLAN_TASKS = 5
MAX_PLAN_RETRIES = 2

# Length choice from the sidebar -> target word count + how many outline
# sections that should take. Keeps the outline sized to what was actually
# asked for instead of always aiming for "5-9 tasks" no matter the length.
LENGTH_PRESETS = {
    "short": {"total_words": (500, 900), "min_tasks": 3, "max_tasks": 4},
    "medium": {"total_words": (1000, 1800), "min_tasks": 5, "max_tasks": 7},
    "long": {"total_words": (2200, 3500), "min_tasks": 7, "max_tasks": 9},
}
DEFAULT_LENGTH = "medium"

RECENCY_DAYS_BY_MODE = {
    "open_book": 7,
    "hybrid": 45,
    "closed_book": 3650,
}

# Language choice from the sidebar -> the actual instruction dropped
# into the orchestrator/worker prompts. Keeping the instruction text
# here (not just "english"/"nepali") means the wording only needs
# tuning in one place if a model ever needs a stronger nudge to
# actually write in Devanagari instead of transliterating/reverting
# to English mid-draft.
LANGUAGE_OPTIONS = {
    "english": "English",
    "nepali": "Nepali - write in the Devanagari script (नेपाली), not romanized/transliterated Nepali.",
}
DEFAULT_LANGUAGE = "english"

# ---- Audience / structure / citations (sidebar quick controls) ----
# Same pattern as LANGUAGE_OPTIONS above: the sidebar only ever sends a
# short internal key ("beginners", "diagram", etc.), and the actual
# instruction text the model sees lives here in one place. Empty string
# key means "auto -- let the model decide", used when the user leaves
# a control on its default option.
AUDIENCE_OPTIONS = {
    "": "",
    "beginners": "complete beginners with little to no background in the topic",
    "practitioners": "practitioners/engineers who already work in this space day-to-day",
    "executives": "non-technical executives or decision-makers evaluating this at a high level",
    "students": "students learning this for the first time in a course-like setting",
}

# blog_kind values match Plan.blog_kind's Literal options in schemas.py
# exactly, so forcing plan.blog_kind = STRUCTURE_OPTIONS[key] is always
# a valid value -- no separate mapping/translation step needed.
STRUCTURE_OPTIONS = {
    "": "",
    "explainer": "explainer",
    "tutorial": "tutorial",
    "comparison": "comparison",
    "news_roundup": "news_roundup",
    "system_design": "system_design",
}

CITATION_MODES = {"auto", "always", "never"}
DEFAULT_CITATION_MODE = "auto"

IMAGE_STYLE_OPTIONS = {
    "": "",
    "diagram": "clean technical diagram style: labeled boxes/arrows, minimal color, whiteboard-like",
    "flat": "flat vector illustration style, muted color palette, simple shapes, no text in the image",
    "sketch": "hand-drawn whiteboard sketch style, black ink linework on a white background",
    "photorealistic": "photorealistic, high detail, natural lighting",
}

# ---- Images (local Stable Diffusion via diffusers, CPU) ----
# Replaced the Google AI Studio path entirely - that one needed a
# billing-linked Google account to get real quota, and even then every
# call would've cost money. This runs fully offline instead: sd-turbo
# is a distilled model that only needs 1-4 inference steps, which is
# what makes CPU generation workable at all (a normal ~50-step SD model
# would take minutes per image on CPU). See backend/local_image_gen.py.
LOCAL_IMAGE_MODEL = "stabilityai/sd-turbo"
LOCAL_IMAGE_STEPS = 2
LOCAL_IMAGE_GUIDANCE_SCALE = 0.0
LOCAL_IMAGE_SIZE = 512
IMAGES_DIR_NAME = "images"
MAX_IMAGES_PER_POST = 3
