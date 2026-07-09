"""Renders the generated blog as one typeset article - headings,
lists, code blocks, quotes, images all styled consistently - instead
of Streamlit's plain default markdown output.

Reads the exact same markdown string and images/ directory the backend
already writes to. Doesn't change what the backend generates, only how
it gets displayed:

- Local image refs (![alt](images/foo.png)) get inlined as base64 data
  URIs and rendered as real <img> tags inside one continuous HTML
  article, instead of interrupting the flow with separate st.image()
  widgets.
- The backend's graceful "image generation failed" fallback text (a
  blockquote starting with **[IMAGE GENERATION FAILED]**, written by
  generate_and_place_images() in backend/reducer/images.py) gets
  detected and shown as a styled callout card instead of a raw
  blockquote, so a failed image reads as an intentional status message
  rather than a rendering glitch.
- A caption line (*like this*) right after an image gets styled as a
  figure caption via CSS.

Also turns the worker's [Source](URL) links (see WORKER_SYSTEM in
backend/nodes/worker.py - it already asks the model to cite evidence
URLs inline) into numbered footnote markers with a References list at
the end, whenever the URL matches one of the run's retrieved evidence
items. No new backend call needed - it's a deterministic post-process
over data the pipeline already returns.
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown as _markdown_lib
import streamlit as st

from ui.icons import icon as _icon

_MD_IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)")

_FAILED_IMAGE_RE = re.compile(
    r"^> \*\*\[IMAGE GENERATION FAILED\]\*\* ?(?P<caption>.*)\n"
    r">\s*\n"
    r"> \*\*Alt:\*\* ?(?P<alt>.*)\n"
    r">\s*\n"
    r"> \*\*Prompt:\*\* ?(?P<prompt>.*)\n"
    r">\s*\n"
    r"> \*\*Error:\*\* ?(?P<error>.*)\n?",
    re.MULTILINE,
)


def _failed_image_callout(match: "re.Match[str]") -> str:
    caption = match.group("caption").strip()
    alt = match.group("alt").strip()
    prompt = match.group("prompt").strip()
    error = match.group("error").strip()
    title = caption or alt or "Image unavailable"
    return (
        "\n\n"
        '<div class="bwa-callout-warning">'
        f'<div class="bwa-callout-icon">{_icon("alert-triangle")}</div>'
        '<div>'
        f'<div class="bwa-callout-title">Image could not be generated: {title}</div>'
        '<div class="bwa-callout-body">'
        "This section was planned to include an illustration, but the image "
        "generation call failed (commonly an invalid/missing image-model API "
        "key, a quota limit, or a safety block). The rest of the post is "
        "unaffected."
        "<details><summary>Details</summary>"
        f'<pre class="bwa-callout-pre">Prompt: {prompt}\nError: {error}</pre>'
        "</details></div></div></div>\n\n"
    )


def _missing_local_image_callout(src: str, alt: str) -> str:
    return (
        "\n\n"
        '<div class="bwa-callout-warning">'
        f'<div class="bwa-callout-icon">{_icon("image")}</div>'
        '<div>'
        f'<div class="bwa-callout-title">Image not found</div>'
        f'<div class="bwa-callout-body">Expected an image at <code>{src}</code>'
        f'{" (" + alt + ")" if alt else ""}, but the file doesn\'t exist on disk.</div>'
        "</div></div>\n\n"
    )


def _mime_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "image/png"


def _inline_local_images(md: str) -> str:
    """Swaps local ![alt](src) refs for base64 data URIs so the whole
    article - text and images - renders as one HTML blob."""

    def _replace(match: "re.Match[str]") -> str:
        alt = match.group("alt")
        src = match.group("src").strip()
        if src.startswith(("http://", "https://", "data:")):
            return match.group(0)

        img_path = Path(src.strip().lstrip("./")).resolve()
        if not img_path.exists():
            return _missing_local_image_callout(src, alt)

        try:
            data = img_path.read_bytes()
        except OSError:
            return _missing_local_image_callout(src, alt)

        encoded = base64.b64encode(data).decode("ascii")
        data_uri = f"data:{_mime_for(img_path)};base64,{encoded}"
        return f"![{alt}]({data_uri})"

    return _MD_IMG_RE.sub(_replace, md)


_ANCHOR_RE = re.compile(r'<a\s+href="(?P<url>[^"]+)"([^>]*)>(?P<text>.*?)</a>', re.IGNORECASE | re.DOTALL)


def _add_citation_markers(body_html: str, evidence: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
    """Numbers evidence in list order and drops a <sup>[N]</sup> after
    any <a href="..."> whose URL matches one of those items. Returns
    the updated HTML plus the ordered, de-duped list of evidence items
    that actually got cited at least once - so the References list
    never shows a source the article didn't actually link to."""
    if not evidence:
        return body_html, []

    url_index: Dict[str, int] = {}
    ordered_cited: List[Dict[str, Any]] = []

    def _index_for(url: str) -> Optional[int]:
        if url not in url_index:
            match = next((e for e in evidence if e.get("url") == url), None)
            if match is None:
                return None
            url_index[url] = len(ordered_cited) + 1
            ordered_cited.append(match)
        return url_index[url]

    def _replace(match: "re.Match[str]") -> str:
        number = _index_for(match.group("url"))
        if number is None:
            return match.group(0)
        return f'{match.group(0)}<sup class="bwa-cite">[{number}]</sup>'

    return _ANCHOR_RE.sub(_replace, body_html), ordered_cited


def _reference_item_html(index: int, item: Dict[str, Any]) -> str:
    url = item.get("url", "")
    title = item.get("title") or url
    meta_bits = [bit for bit in (item.get("source"), item.get("published_at")) if bit]
    meta = f' <span class="bwa-ref-meta">({html.escape(" &middot; ".join(meta_bits))})</span>' if meta_bits else ""
    return (
        f'<li id="bwa-ref-{index}">'
        f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(title)}</a>{meta}'
        "</li>"
    )


def _references_html(cited: List[Dict[str, Any]]) -> str:
    if not cited:
        return ""
    items = "".join(_reference_item_html(i, item) for i, item in enumerate(cited, start=1))
    return f'<div class="bwa-references"><h2>References</h2><ol>{items}</ol></div>'


def to_article_html(md: str, evidence: Optional[List[Dict[str, Any]]] = None) -> str:
    """Converts the backend's markdown into the styled article HTML -
    local images, failed-image callouts, and evidence-linked citation
    markers all handled along the way."""
    processed = _FAILED_IMAGE_RE.sub(_failed_image_callout, md)
    processed = _inline_local_images(processed)
    body_html = _markdown_lib.markdown(
        processed,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    body_html, cited = _add_citation_markers(body_html, evidence or [])
    body_html += _references_html(cited)
    return f'<div class="bwa-article-shell"><div class="bwa-article">{body_html}</div></div>'


def render_article(md: str, evidence: Optional[List[Dict[str, Any]]] = None) -> None:
    """Renders the full article viewer for a generated (or reopened) blog.

    evidence is the run's evidence list (plain dicts or objects with
    .model_dump()) - pass it so [Source](URL) links the worker already
    writes get turned into numbered citations with a References
    section. Safe to leave out (e.g. a reopened post with no evidence
    on hand) - the article just renders without citation markers.
    """
    if not md.strip():
        from ui.components import empty_state

        empty_state(
            "Nothing to preview yet",
            "This post has no content to render.",
            icon="file-text",
        )
        return

    normalized_evidence = [e.model_dump() if hasattr(e, "model_dump") else e for e in (evidence or [])]
    st.markdown(to_article_html(md, normalized_evidence), unsafe_allow_html=True)
