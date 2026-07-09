"""Drives the compiled LangGraph pipeline (bwa_backend.app) and reports
progress via plain callbacks - no Streamlit, no HTML, no styling here.

Same run/streaming/timing logic that used to live inline in
bwa_frontend.py (stream_graph, _node_name_from_update, _merge_state,
run_pipeline), pulled out so the UI layer just decides how to *show*
progress without needing to know about CSS classes or widgets. Also
exposes regenerate_section() and splice_section() for the "regenerate
this section" UI action, and a live token-delta callback (on_token) for
the streaming draft preview.
"""
from __future__ import annotations

import re
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from bwa_backend import app as blog_graph
from bwa_backend import regenerate_section as _regenerate_section
from bwa_backend import revise_draft as _revise_draft

# ------------------------------------------------------------------
# File helpers (slugs, zip bundles) - moved out of the UI file, same
# behavior as before.
# ------------------------------------------------------------------
def safe_slug(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9 _-]+", "", slug)
    slug = re.sub(r"\s+", "_", slug).strip("_")
    return slug or "blog"


def bundle_zip(md_text: str, md_filename: str, images_dir: Path) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(md_filename, md_text.encode("utf-8"))
        if images_dir.is_dir():
            for path in images_dir.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(path))
    return buf.getvalue()


def images_zip(images_dir: Path) -> Optional[bytes]:
    if not images_dir.is_dir():
        return None
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in images_dir.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(path))
    return buf.getvalue()


# ------------------------------------------------------------------
# Graph execution + timing
# ------------------------------------------------------------------
def stream_graph(inputs: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    """Streams graph progress, trying the mode that also carries live
    per-token "custom" events (see backend/nodes/worker.py) first, then
    falling back in order to: plain single-mode streaming (older
    LangGraph versions without multi-mode/custom streams), then a
    single blocking invoke.

    Yields ("updates" | "values" | "custom" | "final", payload).
    """
    for base_mode in ("updates", "values"):
        try:
            for mode, payload in blog_graph.stream(inputs, stream_mode=[base_mode, "custom"]):
                yield (mode, payload)
            yield ("final", blog_graph.invoke(inputs))
            return
        except Exception:
            continue

    for stream_mode in ("updates", "values"):
        try:
            for step in blog_graph.stream(inputs, stream_mode=stream_mode):
                yield (stream_mode, step)
            yield ("final", blog_graph.invoke(inputs))
            return
        except Exception:
            continue

    yield ("final", blog_graph.invoke(inputs))


def _node_name_from_update(payload: Any) -> Optional[str]:
    if isinstance(payload, dict) and len(payload) == 1:
        (key, value), = payload.items()
        if isinstance(value, dict):
            return key
    return None


def _merge_state(current: Dict[str, Any], payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        node_name = _node_name_from_update(payload)
        current.update(payload[node_name] if node_name else payload)
    return current


OnStep = Callable[[str, float], None]
OnTick = Callable[[List[str], Dict[str, Dict[str, float]]], None]
OnToken = Callable[[dict], None]


def run_pipeline(
    inputs: Dict[str, Any],
    on_step: Optional[OnStep] = None,
    on_tick: Optional[OnTick] = None,
    on_token: Optional[OnToken] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Drives the graph, firing callbacks as nodes complete, returns
    (final_state, timing_summary).

    on_step(node_name, elapsed_seconds) fires once per completed node
    (status log line). on_tick(order, timings) fires after every state
    update (re-renders the live progress view). on_token(event) fires
    for each live section-drafting delta ({"type": "section_delta",
    "task_id": ..., "delta": ...}) while a worker streams its section -
    if the installed LangGraph/model don't support that, it just never
    fires and everything else works the same.

    Timing is wall-clock time between one node finishing and the next,
    off the same event stream the tracker renders from. It's an
    approximation for parallel branches (multiple worker calls firing
    at once all get lumped into "worker"), but gives a real sense of
    where the run's time actually goes.
    """
    current_state: Dict[str, Any] = {}
    timings: Dict[str, Dict[str, float]] = {}
    order: List[str] = []

    run_start = time.monotonic()
    last_tick = run_start
    final_state: Dict[str, Any] = {}

    for kind, payload in stream_graph(inputs):
        if kind == "final":
            final_state = payload
            continue

        if kind == "custom":
            if on_token:
                on_token(payload)
            continue

        node_name = _node_name_from_update(payload)
        now = time.monotonic()
        elapsed = now - last_tick
        last_tick = now

        if node_name:
            if node_name not in timings:
                timings[node_name] = {"count": 0, "total": 0.0}
                order.append(node_name)
            timings[node_name]["count"] += 1
            timings[node_name]["total"] += elapsed
            if on_step:
                on_step(node_name, elapsed)

        current_state = _merge_state(current_state, payload)
        if on_tick:
            on_tick(order, timings)

    total_seconds = time.monotonic() - run_start
    if on_tick:
        on_tick(order, timings)

    if not final_state:
        final_state = current_state

    summary = {
        "total_seconds": total_seconds,
        "by_node": timings,
        "order": order,
    }
    return final_state, summary


# ------------------------------------------------------------------
# Per-section regenerate
# ------------------------------------------------------------------
_SECTION_SPLIT_RE = re.compile(r"(?=^## )", re.MULTILINE)


def regenerate_section(
    *,
    task: dict,
    topic: str,
    mode: str,
    as_of: str,
    recency_days: int,
    plan: dict,
    evidence: list,
    language: str = "",
) -> str:
    """Re-drafts one section - thin wrapper around the backend's own
    regenerate_section, kept here so the frontend only ever imports
    from pipeline, never bwa_backend, directly."""
    return _regenerate_section(
        task=task,
        topic=topic,
        mode=mode,
        as_of=as_of,
        recency_days=recency_days,
        plan=plan,
        evidence=evidence,
        language=language,
    )


def splice_section(full_md: str, section_index: int, new_section_md: str) -> str:
    """Replaces the Nth (0-indexed) level-2 ("## ") section in full_md
    with new_section_md, leaving the title and every other section
    untouched.

    Used after regenerate_section() to drop a redrafted section back
    into the post without disturbing anything else (other sections'
    text, already-placed images, etc). If section_index can't be found
    (unexpected structure), just returns full_md unchanged instead of
    guessing.
    """
    parts = _SECTION_SPLIT_RE.split(full_md)  # parts[0] is the '# Title' preamble
    target = section_index + 1
    if target >= len(parts):
        return full_md
    parts[target] = new_section_md.strip() + "\n\n"
    return "".join(parts)


# ------------------------------------------------------------------
# Revise an imported draft
# ------------------------------------------------------------------
def revise_draft(draft_md: str, instruction: str) -> str:
    """Thin wrapper around the backend's own revise_draft, kept here so
    the frontend only ever imports from pipeline, never bwa_backend,
    directly. Used by the "Revise a draft" sidebar action."""
    return _revise_draft(draft_md, instruction)
