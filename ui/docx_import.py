"""Pulls plain-ish Markdown back out of an uploaded .docx file.

Counterpart to ui/docx_export.py (which goes the other way, Markdown ->
docx). Used by the "Revise a draft" flow so someone who wrote their
draft in Word can still import it - doesn't need to be perfect, just
close enough that the revise LLM call has real structure (headings,
paragraphs, lists) to work with instead of one wall of text.
"""
from __future__ import annotations

from io import BytesIO

from docx import Document

# Maps python-docx's built-in heading style names to a Markdown "#"
# prefix. Anything not in here (Normal, List Paragraph, etc.) falls
# back to a plain paragraph.
_HEADING_PREFIXES = {
    "Heading 1": "#",
    "Heading 2": "##",
    "Heading 3": "###",
    "Heading 4": "####",
    "Title": "#",
}


def docx_bytes_to_markdown(data: bytes) -> str:
    """Reads a .docx file's paragraphs top to bottom and turns them into
    Markdown - headings become "# "/"## " lines, list-styled paragraphs
    become "- " bullets, everything else stays a plain paragraph.

    This is a one-way, best-effort conversion (no tables/images), good
    enough to hand a draft's structure to the revise LLM call - not
    meant to round-trip perfectly back to the original .docx.
    """
    doc = Document(BytesIO(data))
    lines: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            lines.append("")
            continue

        style_name = (paragraph.style.name if paragraph.style else "") or ""
        prefix = _HEADING_PREFIXES.get(style_name)

        if prefix:
            lines.append(f"{prefix} {text}")
        elif "List" in style_name or "Bullet" in style_name:
            lines.append(f"- {text}")
        else:
            lines.append(text)

    return "\n\n".join(line for line in lines if line != "").strip()


def extract_draft_text(filename: str, data: bytes) -> str:
    """Extracts plain Markdown/text from an uploaded draft, dispatching
    on file extension. .md/.txt are already text; .docx goes through
    docx_bytes_to_markdown(). Raises ValueError for anything else so
    the caller can show a clear "unsupported file type" message."""
    lower_name = filename.lower()
    if lower_name.endswith(".docx"):
        return docx_bytes_to_markdown(data)
    if lower_name.endswith((".md", ".txt")):
        return data.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {filename}")
