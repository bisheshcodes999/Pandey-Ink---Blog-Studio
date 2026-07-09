"""Image placement + generation - decides which outline sections need
an illustration, generates them locally via Stable Diffusion (no API
key, no billing, no network calls beyond the one-time model download),
and splices each one directly under its section's heading in the
finished post - readers see the illustration inline in the blog
itself, not as a separate downloadable gallery.

The pure string-splicing logic (safe_slug, heading matching, insertion)
lives in image_placement.py instead of here, so it's unit-testable
without pulling in LangChain/diffusers - see tests/test_image_placement.py.
"""
from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import IMAGE_STYLE_OPTIONS, IMAGES_DIR_NAME, MAX_IMAGES_PER_POST
from backend.llm_client import llm
from backend.local_image_gen import generate_image_bytes
from backend.logging_utils import get_logger
from backend.reducer.image_placement import failed_image_block, insert_after_heading, safe_slug
from backend.schemas import ImagePlan
from backend.state import State

logger = get_logger(__name__)

DECIDE_IMAGES_SYSTEM = f"""You are an expert technical editor.
Decide which sections of THIS blog's outline would materially benefit from
an illustration (a diagram, flow, or comparison visual) -- most posts don't
need one for every section.

Rules:
- Max {MAX_IMAGES_PER_POST} images total, each tied to exactly one section_id from the outline given below.
- One image per section at most.
- Only pick a section if a visual would materially improve understanding of it -- avoid decorative images.
- If nothing in the outline warrants an illustration, return images=[].
Return strictly ImagePlan.
"""


def decide_images(state: State) -> dict:
    """Decides which outline sections need an illustration and what to
    generate for each - returns section-tagged specs only. There's no
    document rewrite here (the old approach asked the model to
    reproduce the whole multi-thousand-word draft with placeholders
    inserted, which was slow and occasionally lost/altered text);
    generate_and_place_images() below places each image deterministically
    with plain string splicing instead.

    Skips the planning call entirely when the sidebar's "Include images"
    toggle is off -- include_images defaults to True so older callers
    behave exactly as before this option existed."""
    plan = state["plan"]
    assert plan is not None

    if not state.get("include_images", True):
        return {"image_specs": []}

    planner = llm.with_structured_output(ImagePlan)

    style_key = (state.get("image_style") or "").strip()
    style_instruction = IMAGE_STYLE_OPTIONS.get(style_key, "")
    style_line = (
        f"Image style: every image prompt you write must explicitly specify this visual "
        f"style: {style_instruction}\n"
        if style_instruction else ""
    )

    outline_text = "\n".join(f"- id={t.id}: {t.title} -- {t.goal}" for t in plan.tasks)

    image_plan = planner.invoke(
        [
            SystemMessage(content=DECIDE_IMAGES_SYSTEM),
            HumanMessage(
                content=(
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Topic: {state['topic']}\n"
                    f"{style_line}\n"
                    f"Outline sections:\n{outline_text}\n"
                )
            ),
        ]
    )

    # Guards against a model hiccup: an invented section_id (not in the
    # real outline) would never find a heading to attach to, and two
    # images for the same section would just stack awkwardly - both
    # get filtered out here rather than surfacing as a rendering bug
    # later in generate_and_place_images.
    valid_ids = {t.id for t in plan.tasks}
    seen_sections: set = set()
    deduped = []
    for img in image_plan.images:
        if img.section_id in valid_ids and img.section_id not in seen_sections:
            seen_sections.add(img.section_id)
            deduped.append(img)

    specs = [img.model_dump() for img in deduped[:MAX_IMAGES_PER_POST]]
    return {"image_specs": specs}


def _on_heading_miss(title: str) -> None:
    logger.warning(
        "Couldn't find heading %r to place an image under; appending it at the end instead.",
        title,
    )


def generate_and_place_images(state: State) -> dict:
    """Generates each planned image (skips ones already on disk) and
    splices it directly under its assigned section's heading in the
    final markdown - the image lives inline in the blog itself (and in
    the exported Word doc, which just walks this same markdown), not
    in a separate gallery. A failed image doesn't fail the whole post -
    its spot gets a visible "[IMAGE GENERATION FAILED]" note instead
    (the frontend renders that as a proper callout).

    If the very first image fails, every other image in this run gets
    skipped right away with a short note instead of repeating what's
    very likely the same failure (missing dependency, out-of-memory,
    a corrupted cached download) more times over on a CPU-bound call
    that isn't fast to begin with."""
    plan = state["plan"]
    assert plan is not None

    md = state["merged_md"]
    image_specs = state.get("image_specs", []) or []
    title_by_id = {t.id: t.title for t in plan.tasks}

    if not image_specs:
        filename = f"{safe_slug(plan.blog_title)}.md"
        Path(filename).write_text(md, encoding="utf-8")
        return {"final": md}

    images_dir = Path(IMAGES_DIR_NAME)
    images_dir.mkdir(exist_ok=True)

    generation_broken = False
    first_error = ""

    for spec in image_specs:
        section_title = title_by_id.get(spec["section_id"], plan.blog_title)
        filename = spec["filename"]
        out_path = images_dir / filename

        if not out_path.exists():
            if generation_broken:
                block = failed_image_block(
                    spec,
                    f"Skipped -- local image generation already failed earlier in "
                    f"this run: {first_error}",
                )
                md = insert_after_heading(md, section_title, block, on_miss=_on_heading_miss)
                continue

            try:
                img_bytes = generate_image_bytes(spec["prompt"])
                out_path.write_bytes(img_bytes)
            except Exception as exc:
                logger.warning("Image generation failed for %s: %s", filename, exc)
                generation_broken = True
                first_error = str(exc)
                md = insert_after_heading(
                    md, section_title, failed_image_block(spec, str(exc)), on_miss=_on_heading_miss
                )
                continue

        img_md = f"![{spec['alt']}]({IMAGES_DIR_NAME}/{filename})\n*{spec['caption']}*"
        md = insert_after_heading(md, section_title, img_md, on_miss=_on_heading_miss)

    filename = f"{safe_slug(plan.blog_title)}.md"
    Path(filename).write_text(md, encoding="utf-8")
    return {"final": md}
