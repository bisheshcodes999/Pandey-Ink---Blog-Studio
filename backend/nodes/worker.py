"""Worker node - drafts a single outline section in Markdown.

Also exposes regenerate_section(), which reuses the same prompt-
building logic outside the graph so the UI can redraft one section
without rerunning the whole pipeline.
"""
from __future__ import annotations

from typing import Any, Callable, List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from backend.config import DEFAULT_LANGUAGE, LANGUAGE_OPTIONS, MAX_EVIDENCE_FOR_WORKER_PROMPT
from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import EvidenceItem, Plan, Task

logger = get_logger(__name__)

WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Constraints:
- Cover ALL bullets in order.
- Target words +-15%.
- Output only section markdown starting with "## <Section Title>".
- Write the whole section in the language given below (see "Language:"), including
  the heading itself. Keep this consistent for the entire section, don't drift back
  to English partway through.

Scope guard:
- If blog_kind=="news_roundup", do NOT drift into tutorials (scraping/RSS/how to fetch).
  Focus on events + implications.

Grounding:
- If mode=="open_book": do not introduce any specific event/company/model/funding/policy claim unless supported by provided Evidence URLs.
  For each supported claim, attach a Markdown link ([Source](URL)).
  If unsupported, write "Not found in provided sources."
- If requires_citations==true (hybrid tasks): cite Evidence URLs for external claims.
- NEVER invent a citation. Only use [Source](URL) with a URL that appears verbatim in the
  provided Evidence list. If the Evidence list is empty or has nothing relevant to a claim,
  do not fabricate a version number, date, statistic, partnership, or URL to support it --
  either drop the claim or write it as general background knowledge with no citation at all.
  A placeholder-looking link (e.g. example.com, "/think", or anything not copied from
  Evidence) is worse than no link.

Code:
- If requires_code==true, include at least one minimal snippet.
"""

# no-op fallback for when LangGraph's stream writer isn't available
# (old version, or the graph run isn't currently streaming)
_NULL_WRITER: Callable[[Any], None] = lambda _event: None


def _get_stream_writer() -> Callable[[Any], None]:
    """Grabs LangGraph's custom stream writer if this version supports
    it, otherwise falls back to a no-op. This is what lets worker_node
    emit live per-token section drafts (pipeline.py picks these up as
    stream_mode="custom" events) without hard-depending on an API that
    might not exist in whatever LangGraph version is installed."""
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        return _NULL_WRITER


def _build_worker_messages(task: Task, plan: Plan, context: dict, evidence: List[EvidenceItem]) -> List[BaseMessage]:
    """Builds the system/human messages for drafting `task`. Shared by
    worker_node (inside the graph) and regenerate_section (outside it)
    so a regenerated section gets the exact same context/instructions
    as the original run."""
    bullets_text = "\n- " + "\n- ".join(task.bullets)
    evidence_text = "\n".join(
        f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}"
        for e in evidence[:MAX_EVIDENCE_FOR_WORKER_PROMPT]
    )

    language_key = context.get("language") or DEFAULT_LANGUAGE
    language_instruction = LANGUAGE_OPTIONS.get(language_key, LANGUAGE_OPTIONS[DEFAULT_LANGUAGE])

    return [
        SystemMessage(content=WORKER_SYSTEM),
        HumanMessage(
            content=(
                f"Blog title: {plan.blog_title}\n"
                f"Audience: {plan.audience}\n"
                f"Tone: {plan.tone}\n"
                f"Blog kind: {plan.blog_kind}\n"
                f"Constraints: {plan.constraints}\n"
                f"Language: {language_instruction}\n"
                f"Topic: {context['topic']}\n"
                f"Mode: {context.get('mode')}\n"
                f"As-of: {context.get('as_of')} (recency_days={context.get('recency_days')})\n\n"
                f"Section title: {task.title}\n"
                f"Goal: {task.goal}\n"
                f"Target words: {task.target_words}\n"
                f"Tags: {task.tags}\n"
                f"requires_research: {task.requires_research}\n"
                f"requires_citations: {task.requires_citations}\n"
                f"requires_code: {task.requires_code}\n"
                f"Bullets:{bullets_text}\n\n"
                f"Evidence (ONLY cite these URLs):\n{evidence_text}\n"
            )
        ),
    ]


def _draft_section(messages: List[BaseMessage], task_id: int) -> str:
    """Runs the drafting call. Streams token by token when it can,
    emitting {"type": "section_delta", ...} events via the stream
    writer for the live preview in the UI. Falls back to one blocking
    call if streaming isn't available or breaks partway through."""
    writer = _get_stream_writer()
    chunks: List[str] = []
    try:
        for chunk in llm.stream(messages):
            piece = getattr(chunk, "content", "") or ""
            if piece:
                chunks.append(piece)
                writer({"type": "section_delta", "task_id": task_id, "delta": piece})
        section_md = "".join(chunks).strip()
        if section_md:
            return section_md
        logger.warning("Streamed draft for section %s was empty; retrying without streaming.", task_id)
    except Exception:
        logger.warning("Streaming draft failed for section %s; falling back to a single call.", task_id, exc_info=True)

    return llm.invoke(messages).content.strip()


def worker_node(payload: dict) -> dict:
    """Drafts one section. `payload` is whatever fanout() sent via
    Send("worker", payload) - a single task plus just enough shared
    context (topic/mode/plan/evidence) to write it."""
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]

    messages = _build_worker_messages(task, plan, payload, evidence)
    section_md = _draft_section(messages, task.id)

    return {"sections": [(task.id, section_md)]}


def regenerate_section(
    task: dict,
    topic: str,
    mode: str,
    as_of: str,
    recency_days: int,
    plan: dict,
    evidence: list,
    language: str = "",
) -> str:
    """Re-drafts one section outside the graph - same prompt, same
    grounding rules, same streaming, same language as the original run.
    Used by the UI's "Regenerate this section" button."""
    task_obj = Task(**task)
    plan_obj = Plan(**plan)
    evidence_objs = [EvidenceItem(**e) for e in (evidence or [])]
    context = {"topic": topic, "mode": mode, "as_of": as_of, "recency_days": recency_days, "language": language}

    messages = _build_worker_messages(task_obj, plan_obj, context, evidence_objs)
    return _draft_section(messages, task_obj.id)
