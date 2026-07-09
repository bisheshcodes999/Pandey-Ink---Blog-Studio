"""Research node - runs Tavily searches for the router's queries, then
asks the LLM to normalize the raw results into EvidenceItems.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import (
    MAX_RESEARCH_QUERIES,
    MAX_RESULTS_PER_QUERY,
    RECENCY_DAYS_BY_MODE,
    TAVILY_API_KEY,
)
from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import EvidencePack
from backend.state import State

logger = get_logger(__name__)

RESEARCH_SYSTEM = """You are a research synthesizer.

Given raw web search results, produce EvidenceItem objects.

Rules:
- Only include items with a non-empty url.
- Prefer relevant + authoritative sources.
- Normalize published_at to ISO YYYY-MM-DD if reliably inferable; else null (do NOT guess).
- Keep snippets short.
- Deduplicate by URL.
"""


def _tavily_search(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> List[dict]:
    """Runs one Tavily query, normalizes to plain dicts. Returns []
    instead of raising if Tavily isn't configured or the call fails -
    one bad query shouldn't kill the whole research step."""
    if not TAVILY_API_KEY:
        return []
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults  # type: ignore

        tool = TavilySearchResults(max_results=max_results)
        results = tool.invoke({"query": query})
        return [
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": r.get("content") or r.get("snippet") or "",
                "published_at": r.get("published_date") or r.get("published_at"),
                "source": r.get("source"),
            }
            for r in (results or [])
        ]
    except Exception:
        logger.warning("Tavily search failed for query %r; continuing without it.", query, exc_info=True)
        return []


def _iso_to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _no_evidence_fallback(state: State) -> dict:
    """Router thought this topic needed live research but nothing real
    came back - that's usually a sign the topic is actually evergreen
    (vague/general subject) and the router guessed wrong, not that the
    topic is genuinely volatile. Downgrading to closed_book here stops
    the orchestrator from framing it as a "news roundup" with nothing
    to report, which is exactly what pushes the drafting model to
    invent fake specifics (version numbers, dates, citation-looking
    links) to fill the gap."""
    logger.warning(
        "No research evidence found for %r (mode=%r); downgrading to closed_book so the "
        "post is drafted as a general explainer instead of a news roundup with nothing to "
        "report.", state["topic"], state.get("mode"),
    )
    return {
        "evidence": [],
        "mode": "closed_book",
        "recency_days": RECENCY_DAYS_BY_MODE["closed_book"],
    }


def research_node(state: State) -> dict:
    """Runs each query the router produced, normalizes + dedupes the
    results into EvidenceItems, and filters to the recency window for
    open-book (news/weekly) posts. Falls back to closed_book (see
    _no_evidence_fallback) when nothing real comes back instead of
    handing the orchestrator an empty evidence list under a mode that
    expects it to cite sources."""
    queries = (state.get("queries") or [])[:MAX_RESEARCH_QUERIES]
    raw: List[dict] = []
    for query in queries:
        raw.extend(_tavily_search(query))

    if not raw:
        return _no_evidence_fallback(state)

    extractor = llm.with_structured_output(EvidencePack)
    pack = extractor.invoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(
                content=(
                    f"As-of date: {state['as_of']}\n"
                    f"Recency days: {state['recency_days']}\n\n"
                    f"Raw results:\n{raw}"
                )
            ),
        ]
    )

    deduped_by_url = {e.url: e for e in pack.evidence if e.url}
    evidence = list(deduped_by_url.values())

    if state.get("mode") == "open_book":
        as_of = date.fromisoformat(state["as_of"])
        cutoff = as_of - timedelta(days=int(state["recency_days"]))
        evidence = [e for e in evidence if (d := _iso_to_date(e.published_at)) and d >= cutoff]

    if not evidence:
        return _no_evidence_fallback(state)

    return {"evidence": evidence}
