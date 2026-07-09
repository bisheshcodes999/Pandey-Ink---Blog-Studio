"""Pipeline progress tracker - a row of step chips (done / active /
pending / skipped), one per backend graph node.

Renders off the same data the run loop already produces (node name ->
{count, total} timing dict, built while streaming the LangGraph run).
Adds real completed/current/pending states instead of only ever
showing "done" or "active", and marks nodes the run never touched
(e.g. "research" in closed-book mode) as "skipped" instead of leaving
them looking stuck once the run's over.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ui.icons import icon as _icon

_STATE_ICON = {
    "done": "check-circle",
    "active": "loader",
    "pending": "circle-dashed",
    "skipped": "circle-dashed",
}


def _chip(label: str, state: str, time_s: Optional[float] = None) -> str:
    time_html = f'<span class="t">{time_s:.1f}s</span>' if time_s is not None else ""
    return (
        f'<div class="bwa-step {state}">'
        f'<span class="bwa-step-icon">{_icon(_STATE_ICON.get(state, "circle"))}</span>'
        f"<span>{label}</span>{time_html}</div>"
    )


def build_step_track_html(
    order: List[str],
    timings: Dict[str, Dict[str, float]],
    node_labels: Dict[str, str],
    node_order_hint: List[str],
    *,
    still_running: bool = True,
) -> str:
    """Builds the HTML for the step tracker row.

    order/timings are exactly what run_pipeline() already produces
    (node name -> completion count/total seconds). node_order_hint is
    just the expected node sequence, used only to pre-render the steps
    that haven't finished yet.
    """
    known = set(order)
    extra = [n for n in order if n not in node_order_hint]
    sequence = list(node_order_hint) + extra

    first_pending = next((n for n in node_order_hint if n not in known), None)

    chips: List[str] = []
    for name in sequence:
        label = node_labels.get(name, name)
        if name in known:
            info = timings[name]
            suffix = f" ×{info['count']}" if info["count"] > 1 else ""
            chips.append(_chip(f"{label}{suffix}", "done", info["total"]))
        elif still_running and name == first_pending:
            chips.append(_chip(label, "active"))
        elif still_running:
            chips.append(_chip(label, "pending"))
        else:
            chips.append(_chip(label, "skipped"))

    return f'<div class="bwa-step-track">{"".join(chips)}</div>'
