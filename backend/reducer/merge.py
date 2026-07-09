"""Merges the fanned-out section drafts back into one ordered doc."""
from __future__ import annotations

from backend.state import State


def merge_content(state: State) -> dict:
    """Orders sections by their original task id (fan-out/fan-in doesn't
    guarantee they finish in order) and joins them under the title."""
    plan = state["plan"]
    if plan is None:
        raise ValueError("merge_content called without plan.")

    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda pair: pair[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}
