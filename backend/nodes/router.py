"""Router node - figures out if a topic needs live web research before
planning, and how strict the recency window should be if so.
"""
from __future__ import annotations

from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import RECENCY_DAYS_BY_MODE
from backend.llm_client import llm
from backend.schemas import RouterDecision
from backend.state import State

ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false): evergreen concepts.
- hybrid (needs_research=true): evergreen + needs up-to-date examples/tools/models.
- open_book (needs_research=true): volatile weekly/news/"latest"/pricing/policy.

Default to closed_book. Only choose hybrid or open_book when the TOPIC
TEXT ITSELF contains a clear signal that it is about something current,
volatile, or time-bound -- e.g. it names a specific product/company/
model/version, includes words like "latest", "this week", "news",
"pricing", "release", or refers to a live/ongoing event. A short,
generic, or ambiguous topic (a single common noun, a general subject
like a plant, animal, historical topic, or well-known evergreen concept)
is closed_book, even if you cannot rule out that something recent might
exist about it. Never assume an ambiguous single word or short phrase is
secretly the name of a specific product, company, or piece of software --
treat it as the plain, ordinary meaning of the word unless the topic
text says otherwise.

If needs_research=true:
- Output 3-10 high-signal, scoped queries.
- For open_book weekly roundup, include queries reflecting last 7 days.
"""


def router_node(state: State) -> dict:
    """Classifies the topic into closed/hybrid/open-book, and if
    research is needed, generates the search queries for research_node."""
    decider = llm.with_structured_output(RouterDecision)
    decision = decider.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(
                content=f"Topic: {state['topic']}\nAs-of date: {state['as_of']}"),
        ]
    )

    recency_days = RECENCY_DAYS_BY_MODE.get(
        decision.mode, RECENCY_DAYS_BY_MODE["closed_book"])

    return {
        "needs_research": decision.needs_research,
        "mode": decision.mode,
        "queries": decision.queries,
        "recency_days": recency_days,
    }


def route_next(state: State) -> Literal["research", "orchestrator"]:
    """Skip straight to planning if no research is needed."""
    return "research" if state["needs_research"] else "orchestrator"
