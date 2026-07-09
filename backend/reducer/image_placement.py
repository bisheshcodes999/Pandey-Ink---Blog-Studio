"""Pure string-manipulation helpers for image placement - no LLM calls,
no image generation, no LangChain/diffusers imports. Split out of
images.py on purpose so this logic is unit-testable on its own (see
tests/test_image_placement.py) without needing the full model stack
installed - the exact thing that made the rest of the pipeline hard to
verify in isolation.
"""
from __future__ import annotations

import re
from typing import Pattern


def safe_slug(title: str) -> str:
    """Turns a blog title into a filesystem-safe slug, e.g.
    "How CPUs Work!" -> "how_cpus_work". Falls back to "blog" if
    nothing alphanumeric survives."""
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9 _-]+", "", slug)
    slug = re.sub(r"\s+", "_", slug).strip("_")
    return slug or "blog"


def failed_image_block(spec: dict, error_text: str) -> str:
    """The Markdown blockquote dropped in place of an image that
    failed to generate - ui/blog_viewer.py and ui/docx_export.py both
    detect this exact shape and render it as a styled callout instead
    of raw blockquote text."""
    return (
        f"> **[IMAGE GENERATION FAILED]** {spec.get('caption', '')}\n>\n"
        f"> **Alt:** {spec.get('alt', '')}\n>\n"
        f"> **Prompt:** {spec.get('prompt', '')}\n>\n"
        f"> **Error:** {error_text}\n"
    )


def heading_pattern(title: str) -> Pattern[str]:
    """Matches a section heading exactly as merge_content writes it:
    "## <title>" (worker.py's WORKER_SYSTEM tells the model to start
    every section with "## <Section Title>"). Tolerant of trailing
    punctuation/case drift (a small local model occasionally adds a
    colon or changes case when drafting), but not of a genuinely
    different title -- that's handled by the fallback in
    insert_after_heading."""
    core = re.escape(title.strip().rstrip(".:!?"))
    return re.compile(r"^##[ \t]+" + core + r"[ \t:.!?]*$", re.MULTILINE | re.IGNORECASE)


def insert_after_heading(md: str, title: str, block: str, *, on_miss=None) -> str:
    """Splices `block` directly under the section's "## <title>"
    heading. Falls back to appending at the very end of the document
    (still visible, just not perfectly placed) if the heading text
    doesn't match at all, so a title mismatch never silently drops an
    image.

    `on_miss`, if given, is called with the title when the fallback
    path is taken (images.py passes its logger.warning here; tests can
    pass a list.append to assert on the miss without needing a real
    logger)."""
    match = heading_pattern(title).search(md)
    if match is None:
        if on_miss is not None:
            on_miss(title)
        return md.rstrip() + "\n\n" + block + "\n"
    insert_at = match.end()
    return md[:insert_at] + "\n\n" + block + md[insert_at:]
