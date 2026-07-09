"""Repurposing pass - turns the finished post into ready-to-post social
and newsletter copy, so a single generated post also becomes a small
content campaign instead of just a file to download.

Runs last in the reducer, after images are placed, so it works off the
actual final text the reader sees. Same as fact_check/critic, a failure
here just degrades to an empty result instead of failing the whole run
- repurposing is a bonus, not a requirement.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llm_client import llm
from backend.logging_utils import get_logger
from backend.schemas import RepurposedContent
from backend.state import State

logger = get_logger(__name__)

REPURPOSE_SYSTEM = """You are a social media editor turning an already-written
blog post into other ready-to-post formats. Do not invent new facts, examples,
or claims that aren't in the post -- you are re-shaping existing content, not
writing new content.

Produce three things:
1. twitter_thread: 5-8 tweets. The first tweet is a strong hook (no "thread:"
   or numbering -- that's added by the UI). Each tweet must stand on its own,
   under 280 characters, and the thread overall should walk through the
   post's main points in order.
2. linkedin_post: one post, short punchy paragraphs (1-3 sentences each), an
   attention-grabbing opening line, and a soft call-to-action at the end
   (e.g. inviting comments or shares). 120-220 words.
3. newsletter_blurb: 2-4 sentences written to entice a reader to click
   through and read the full post. No spoilers of the ending/conclusion.

Write all three in the SAME language as the finished post below -- if the post is
in Nepali, the tweets/LinkedIn post/blurb are in Nepali too, not translated to English.

Return strictly a RepurposedContent object.
"""


def repurpose_node(state: State) -> dict:
    """Reads the finished post (final, falling back to merged_md) and
    returns repurposed_content as a plain dict (or None if it failed) -
    State's a TypedDict, no Pydantic models directly."""
    source_md = state.get("final") or state.get("merged_md") or ""

    if not source_md.strip():
        return {"repurposed_content": None}

    repurposer = llm.with_structured_output(RepurposedContent)
    try:
        content = repurposer.invoke(
            [
                SystemMessage(content=REPURPOSE_SYSTEM),
                HumanMessage(content=f"Finished post:\n{source_md}"),
            ]
        )
        return {"repurposed_content": content.model_dump()}
    except Exception:
        logger.warning("Repurposing pass failed; continuing without it.", exc_info=True)
        return {"repurposed_content": None}
