"""Orchestrator node - turns the topic (plus evidence if any) into a
structured outline, then fans it out into one worker call per section.
"""
from __future__ import annotations

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.types import Send

from backend.config import (
    AUDIENCE_OPTIONS,
    DEFAULT_CITATION_MODE,
    DEFAULT_LANGUAGE,
    DEFAULT_LENGTH,
    LANGUAGE_OPTIONS,
    LENGTH_PRESETS,
    MAX_EVIDENCE_FOR_PLANNING_PROMPT,
    MAX_PLAN_RETRIES,
    STRUCTURE_OPTIONS,
)
from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import Plan
from backend.state import State

logger = get_logger(__name__)

ORCH_SYSTEM = """You are a senior technical writer and developer advocate.
Produce a highly actionable outline for a technical blog post.

Requirements:
- Follow the requested target length and section count exactly (given per-run below).
- Each task needs a goal + 3-6 bullets + target_words; set target_words so all tasks
  sum close to the requested total word count.
- Tags are flexible; do not force a fixed taxonomy.
- If a desired tone is given, use it for Plan.tone verbatim -- do not substitute your own.
- Write blog_title and every task's title/goal/bullets in the language given below
  (see "Language:"). This is the language the whole post gets drafted in downstream,
  not just a label -- don't leave it in English if another language was requested.

Grounding:
- closed_book: evergreen, no evidence dependence.
- hybrid: use evidence for up-to-date examples; mark those tasks requires_research=True and requires_citations=True.
- open_book: weekly/news roundup:
  - Set blog_kind="news_roundup"
  - No tutorial content unless requested
  - If evidence is weak, plan should explicitly reflect that (don't invent events).

Output must match Plan schema.
"""


def orchestrator_node(state: State) -> dict:
    """Plans the post - title, audience, tone, and the outline
    (Plan.tasks) that fanout() sends out to workers.

    desired_length/desired_tone come from the sidebar. desired_length
    picks a LENGTH_PRESETS entry (word range + how many sections that
    implies), and desired_tone, when set, gets forced onto Plan.tone
    after the call so every worker prompt picks it up - user's choice
    always wins over whatever the model guessed.

    qwen3:8b doesn't always respect a numeric section-count instruction,
    and a thin outline here means a short, image-less post downstream
    (not much to draft or illustrate). So instead of just accepting
    whatever the first call returns, this retries up to MAX_PLAN_RETRIES
    times with an explicit follow-up when the outline's thinner than the
    requested length implies, then gives up and continues with whatever
    it has.
    """
    planner = llm.with_structured_output(Plan)
    mode = state.get("mode", "closed_book")
    evidence = state.get("evidence", [])

    forced_kind = "news_roundup" if mode == "open_book" else None

    preset = LENGTH_PRESETS.get(state.get("desired_length") or DEFAULT_LENGTH, LENGTH_PRESETS[DEFAULT_LENGTH])
    min_tasks, max_tasks = preset["min_tasks"], preset["max_tasks"]
    words_low, words_high = preset["total_words"]

    desired_tone = (state.get("desired_tone") or "").strip()
    tone_line = f"Desired tone (use for Plan.tone verbatim): {desired_tone}\n" if desired_tone else ""

    language_key = state.get("desired_language") or DEFAULT_LANGUAGE
    language_instruction = LANGUAGE_OPTIONS.get(language_key, LANGUAGE_OPTIONS[DEFAULT_LANGUAGE])
    language_line = f"Language: {language_instruction}\n"

    # Sidebar quick controls -- empty key means "auto, let the model
    # decide", same convention as desired_tone above. Both also get
    # force-applied onto the returned Plan below so the user's choice
    # always wins even if the model ignores the prompt instruction.
    audience_key = (state.get("desired_audience") or "").strip()
    audience_instruction = AUDIENCE_OPTIONS.get(audience_key, "")
    audience_line = f"Intended audience (use for Plan.audience verbatim): {audience_instruction}\n" if audience_instruction else ""

    structure_key = (state.get("desired_blog_kind") or "").strip()
    structure_value = STRUCTURE_OPTIONS.get(structure_key, "")
    structure_line = f"Requested structure (use for Plan.blog_kind): {structure_value}\n" if structure_value else ""

    base_messages: List[BaseMessage] = [
        SystemMessage(content=ORCH_SYSTEM),
        HumanMessage(
            content=(
                f"Topic: {state['topic']}\n"
                f"Mode: {mode}\n"
                f"As-of: {state['as_of']} (recency_days={state['recency_days']})\n"
                f"{tone_line}"
                f"{language_line}"
                f"{audience_line}"
                f"{structure_line}"
                f"Target length: {words_low}-{words_high} words total, across {min_tasks}-{max_tasks} sections.\n"
                f"{'Force blog_kind=news_roundup' if forced_kind else ''}\n\n"
                f"Evidence:\n{[e.model_dump() for e in evidence][:MAX_EVIDENCE_FOR_PLANNING_PROMPT]}"
            )
        ),
    ]

    plan = planner.invoke(base_messages)
    attempt = 1
    while len(plan.tasks) < min_tasks and attempt <= MAX_PLAN_RETRIES:
        logger.warning(
            "Orchestrator returned only %d task(s) for %r (attempt %d/%d); asking for a fuller outline.",
            len(plan.tasks), state["topic"], attempt, MAX_PLAN_RETRIES,
        )
        retry_messages = base_messages + [
            AIMessage(content=f"(That outline only had {len(plan.tasks)} section(s).)"),
            HumanMessage(
                content=(
                    f"That outline only had {len(plan.tasks)} section(s), which is too thin for the "
                    f"requested {words_low}-{words_high} word post. Produce a NEW, COMPLETE outline with "
                    f"at least {min_tasks} distinct sections covering the topic in real depth (background, "
                    "mechanics/how it works, a concrete example or application, trade-offs/limitations, and "
                    "a wrap-up are usually enough to reach that). Return the full Plan again, not just the "
                    "missing sections."
                )
            ),
        ]
        plan = planner.invoke(retry_messages)
        attempt += 1

    if len(plan.tasks) < min_tasks:
        logger.warning(
            "Orchestrator still returned only %d task(s) for %r after %d attempt(s); "
            "continuing with what the model produced rather than blocking the run.",
            len(plan.tasks), state["topic"], attempt - 1,
        )

    if forced_kind:
        plan.blog_kind = "news_roundup"
    elif structure_value:
        plan.blog_kind = structure_value
    if desired_tone:
        plan.tone = desired_tone
    if audience_instruction:
        plan.audience = audience_instruction

    # Citations on/off override -- "auto" leaves whatever the model
    # decided per-task (requires_research/hybrid tasks get citations,
    # closed-book ones don't); "always"/"never" force every task the
    # same way regardless of mode.
    citation_mode = (state.get("citation_mode") or DEFAULT_CITATION_MODE).strip()
    if citation_mode == "always":
        for task in plan.tasks:
            task.requires_citations = True
    elif citation_mode == "never":
        for task in plan.tasks:
            task.requires_citations = False

    return {"plan": plan}


def fanout(state: State) -> List[Send]:
    """Dispatches one worker call per outline task, each with just the
    context that task needs."""
    assert state["plan"] is not None
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "as_of": state["as_of"],
                "recency_days": state["recency_days"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
                "language": state.get("desired_language", ""),
            },
        )
        for task in state["plan"].tasks
    ]
