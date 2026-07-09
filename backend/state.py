"""LangGraph state shared across every node.

Each node returns a partial dict and LangGraph merges it in (field by
field, overwriting - except `sections`, which accumulates across the
fanned-out worker calls instead of overwriting).
"""
from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict
from backend.schemas import EvidenceItem, Plan


class State(TypedDict):
    topic: str

    # sidebar controls, read by orchestrator_node to size/style the
    # outline instead of guessing
    desired_length: str
    desired_tone: str
    desired_language: str
    # quick differentiator controls -- empty string/None means "auto,
    # let the model decide" for each of these, same convention as
    # desired_tone above
    desired_audience: str
    desired_blog_kind: str
    citation_mode: str
    include_images: bool
    image_style: str

    # routing / research
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]
    # recency
    as_of: str
    recency_days: int
    # workers -- (task_id, section_md), accumulated across fanned-out calls
    sections: Annotated[List[tuple[int, str]], operator.add]
    # reducer: merge -> fact-check -> critic -> images -> repurpose
    merged_md: str
    fact_check_findings: List[dict]
    critic_findings: List[dict]
    # each spec is tied to a section_id (see ImageSpec in schemas.py) --
    # generate_and_place_images() in backend/reducer/images.py splices
    # each one directly under its section's heading, no free-floating
    # placeholder/document-rewrite step involved
    image_specs: List[dict]
    final: str
    repurposed_content: Optional[dict]
