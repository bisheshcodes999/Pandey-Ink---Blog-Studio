"""Fact-check pass - flags claims in the merged draft that aren't
clearly backed by the retrieved evidence.

Only runs when there's actual evidence to check against - closed-book
posts have nothing to verify, so it's a free no-op for those. Same as
the image call, a failure here just degrades to empty findings instead
of failing the whole run - a flaky fact-check shouldn't block the post.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import MAX_EVIDENCE_FOR_FACT_CHECK
from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import FactCheckReport
from backend.state import State

logger = get_logger(__name__)

FACT_CHECK_SYSTEM = """You are a careful fact-checking editor reviewing a
drafted technical blog post against a fixed list of evidence sources.

Flag ONLY statements that assert a specific, checkable fact (an event, a
number, a date, a named release, a policy, a quote) that is NOT clearly
supported by the provided evidence. Do not flag general/explanatory
statements, opinions, or well-known evergreen facts.

If every checkable claim is supported, or there are no checkable claims,
return an empty findings list. Be conservative: only flag real gaps, not
stylistic nitpicks.

Write claim/concern in ENGLISH regardless of what language the draft itself is
written in -- this report is for the developer reviewing the run, not the reader.
"""


def fact_check_node(state: State) -> dict:
    """Checks merged_md against evidence, returns flagged claims as
    fact_check_findings (plain dicts - State is a TypedDict, no
    Pydantic models directly)."""
    evidence = state.get("evidence") or []
    merged_md = state.get("merged_md", "")

    if not evidence or not merged_md.strip():
        return {"fact_check_findings": []}

    evidence_text = "\n".join(
        f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}" for e in evidence[:MAX_EVIDENCE_FOR_FACT_CHECK]
    )

    checker = llm.with_structured_output(FactCheckReport)
    try:
        report = checker.invoke(
            [
                SystemMessage(content=FACT_CHECK_SYSTEM),
                HumanMessage(content=f"Evidence:\n{evidence_text}\n\nDraft:\n{merged_md}"),
            ]
        )
        return {"fact_check_findings": [finding.model_dump() for finding in report.findings]}
    except Exception:
        logger.warning("Fact-check pass failed; continuing without findings.", exc_info=True)
        return {"fact_check_findings": []}
