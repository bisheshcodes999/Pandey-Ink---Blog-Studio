"""Pydantic schemas shared across the pipeline.

Every LLM call goes through `.with_structured_output(<schema>)` instead
of parsing free text, so these models are basically the contract each
prompt is written against.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Task(BaseModel):
    """One section of the outline."""

    id: int
    title: str
    goal: str = Field(..., description="One sentence describing what the reader should do/understand.")
    bullets: List[str] = Field(..., min_length=3, max_length=6)
    target_words: int = Field(..., description="Target words (120-550).")

    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    """Full outline: metadata + the list of tasks."""

    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task]


class EvidenceItem(BaseModel):
    """A single retrieved/normalized research source."""

    title: str
    url: str
    published_at: Optional[str] = None  # ISO "YYYY-MM-DD" preferred
    snippet: Optional[str] = None
    source: Optional[str] = None


class RouterDecision(BaseModel):
    """Router output: needs research or not, and why."""

    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    reason: str
    queries: List[str] = Field(default_factory=list)
    max_results_per_query: int = Field(5)


class EvidencePack(BaseModel):
    """Wrapper so the research step can return a list via structured
    output (a bare top-level list isn't a valid schema everywhere)."""

    evidence: List[EvidenceItem] = Field(default_factory=list)


class ImageSpec(BaseModel):
    """One planned illustration, pinned to a specific outline section
    by id - not a free-floating placeholder the model has to place
    itself. backend/reducer/images.py splices it in deterministically
    right under that section's heading, so placement never depends on
    a small local model correctly reproducing the whole document."""

    section_id: int = Field(..., description="Matches Task.id -- which outline section this illustrates.")
    filename: str = Field(..., description="Save under images/, e.g. qkv_flow.png")
    alt: str
    caption: str
    prompt: str = Field(..., description="Prompt to send to the image model.")


class ImagePlan(BaseModel):
    """Output of the image-planning pass - which outline sections (by
    id) get an illustration and what to generate for each. No document
    rewrite involved."""

    images: List[ImageSpec] = Field(default_factory=list)


class FactCheckFinding(BaseModel):
    """One claim in the draft that isn't clearly backed by evidence."""

    section_title: str = Field(..., description="The '## ' heading the claim appears under.")
    claim: str = Field(..., description="The specific claim or statement being flagged.")
    concern: str = Field(..., description="Why this claim isn't clearly supported by the provided evidence.")


class FactCheckReport(BaseModel):
    """Fact-check output. Empty findings = nothing flagged, or there
    was no evidence to check against in the first place."""

    findings: List[FactCheckFinding] = Field(default_factory=list)


class CriticFinding(BaseModel):
    """One argument-quality issue from the adversarial critic pass -
    different from FactCheckFinding, which only checks claims against
    evidence. This one catches weak reasoning even with no evidence at
    all (closed-book posts)."""

    section_title: str = Field(..., description="The '## ' heading the issue appears under.")
    issue_type: Literal[
        "unsupported_claim",
        "overgeneralization",
        "logical_gap",
        "missing_nuance",
        "weak_evidence",
        "unclear_reasoning",
    ]
    critique: str = Field(..., description="The specific weakness, argued adversarially.")
    suggestion: str = Field(..., description="A concrete, one-sentence fix.")


class CriticReport(BaseModel):
    """Critic pass output. Empty findings means it didn't find a real
    weakness worth flagging - it's told to be sparing, not to nitpick
    for the sake of it."""

    findings: List[CriticFinding] = Field(default_factory=list)


class RepurposedContent(BaseModel):
    """Turns a finished post into other formats - same content,
    different shape, so one generated post also becomes ready-to-post
    social/newsletter copy instead of just a file to download."""

    twitter_thread: List[str] = Field(
        default_factory=list,
        description="Each item is one tweet's text (no numbering -- the UI adds that), <=280 chars, first tweet is the hook.",
    )
    linkedin_post: str = Field(
        default_factory=str,
        description="A single LinkedIn-native post: short paragraphs, a hook opening line, ends with a soft call-to-action.",
    )
    newsletter_blurb: str = Field(
        default_factory=str,
        description="2-4 sentences enticing a reader to click through to the full post.",
    )
