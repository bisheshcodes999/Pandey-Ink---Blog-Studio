"""Revise an imported draft based on a user instruction.

Separate from the main generate pipeline (backend/graph.py) on purpose -
revising someone's own draft doesn't need research, planning, or a
fan-out across sections. It's one call: draft in, instruction in,
edited draft out. Kept outside the LangGraph graph entirely, same way
worker.py's regenerate_section() runs outside the graph for the
"regenerate this section" button.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm_client import llm
from backend.logging_utils import get_logger

logger = get_logger(__name__)

REVISE_SYSTEM = """You are a careful editor revising a blog post draft that a human
author already wrote.

Rules:
- Apply ONLY the requested change. Don't rewrite parts of the draft the
  instruction didn't ask about.
- Keep the author's voice, structure, and headings unless the
  instruction specifically asks to change them.
- Keep the same Markdown formatting style as the input (headings,
  lists, code blocks, links) unless asked to change it.
- Output the FULL revised draft in Markdown, start to finish. Don't
  summarize it, don't add commentary about what you changed - just the
  edited post itself.
"""


def revise_draft(draft_md: str, instruction: str) -> str:
    """Sends the draft + edit instruction to the LLM, returns the
    revised Markdown. Raises on an empty response so the UI can show a
    real error instead of silently blanking someone's draft."""
    messages = [
        SystemMessage(content=REVISE_SYSTEM),
        HumanMessage(
            content=(
                f"Requested change: {instruction.strip()}\n\n"
                "Original draft:\n"
                "---\n"
                f"{draft_md.strip()}\n"
                "---\n"
            )
        ),
    ]

    revised = llm.invoke(messages).content.strip()
    if not revised:
        raise RuntimeError("Model returned an empty revision - draft left unchanged.")
    return revised
