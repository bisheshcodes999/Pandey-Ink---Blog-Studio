"""Adversarial critic pass - argues against the drafted post looking
for weak reasoning, not just unsupported facts.

Kept separate from fact_check.py on purpose. That node only checks
claims against retrieved evidence, so it's a no-op for closed-book
posts (nothing to check against). This one has no such gate - runs on
every post, evidence or not, and plays devil's advocate against the
argument itself: overgeneralizations, missing caveats, unclear
reasoning, claims stated more confidently than the draft actually
earns. Same as fact_check_node, a flaky pass here just degrades to an
empty finding list instead of blocking the post.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import CriticReport
from backend.state import State

logger = get_logger(__name__)

CRITIC_SYSTEM = """You are a skeptical senior editor doing an adversarial
read of a drafted blog post. Your job is to argue AGAINST the draft, not
to summarize or praise it.

For each section, look for:
- unsupported_claim: a specific assertion stated as fact with nothing backing it up
- overgeneralization: a claim that's true in some cases stated as if always true
- logical_gap: a conclusion that doesn't actually follow from what came before it
- missing_nuance: a real trade-off, exception, or limitation the draft glosses over
- weak_evidence: a claim technically supported, but by evidence far weaker than the confidence used to state it
- unclear_reasoning: a passage a careful reader could not follow or verify

Be a tough but fair critic:
- Only raise a finding if you can point to the specific sentence or idea that's weak.
- Do not flag stylistic preferences, word choice, or things that are simply short.
- Do not repeat the same underlying issue more than once across sections.
- If the draft is genuinely solid, return an empty findings list -- do not
  manufacture a critique just to have something to say.

For every finding, give one concrete, one-sentence suggestion that would fix it.

Write critique/suggestion in ENGLISH regardless of what language the draft itself is
written in -- this report is for the developer reviewing the run, not the reader.
"""


def critic_node(state: State) -> dict:
    """Reviews merged_md adversarially, returns findings as
    critic_findings (plain dicts - State's a TypedDict)."""
    merged_md = state.get("merged_md", "")

    if not merged_md.strip():
        return {"critic_findings": []}

    critic = llm.with_structured_output(CriticReport)
    try:
        report = critic.invoke(
            [
                SystemMessage(content=CRITIC_SYSTEM),
                HumanMessage(content=f"Draft:\n{merged_md}"),
            ]
        )
        return {"critic_findings": [finding.model_dump() for finding in report.findings]}
    except Exception:
        logger.warning("Critic pass failed; continuing without findings.", exc_info=True)
        return {"critic_findings": []}
