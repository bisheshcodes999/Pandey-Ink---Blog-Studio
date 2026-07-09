"""Streamlit frontend for the Blog Writing Agent.

Thin presentation layer over bwa_backend.app (the compiled LangGraph
pipeline: router -> research? -> orchestrator -> workers -> reducer).
This file only owns rendering, input validation, and run telemetry -
all the agent logic lives in bwa_backend.py and stays untouched here.

Rendering itself is split across the ui/ package (styles, icons, one
module per panel) and pipeline.py (graph streaming + timing). This
file's the orchestrator: wires user input -> pipeline -> session state
-> render, same four-step flow as the old single-file version.
"""
from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

try:
    from bwa_backend import OLLAMA_MODEL
except ImportError:
    OLLAMA_MODEL = "qwen3:8b"

import pipeline
from ui import styles
from ui.blog_viewer import render_article
from ui.components import badge, card_close, card_open, empty_state, section_label
from ui.docx_export import markdown_to_docx_bytes
from ui.docx_import import extract_draft_text
from ui.header import render_header
from ui.icons import icon as _icon
from ui.progress_panel import build_step_track_html
from ui.revise_panel import render_revise_panel
from ui.saved_posts import extract_title_from_md, read_md_file
from ui.sidebar import render_sidebar

# ------------------------------------------------------------------
# Branding / design tokens
# ------------------------------------------------------------------
# APP_NAME is the short brand lockup in the sidebar ("PandeyInk" +
# icon); APP_TITLE is the bigger page title in the main content header
# - kept as two separate strings since the two spots want different
# lengths/framing, not just the same name reused twice. Written as one
# word here (no space) to match how "PandeyInk" reads in the main
# header's brand-accent span.
APP_NAME = "PandeyInk"
APP_TITLE = "PandeyInk - Blog Studio"
APP_TAGLINE = "A local multi-agent pipeline that researches, plans, drafts, and illustrates technical blog posts."

# Friendly labels for backend graph node names, used in the pipeline
# tracker + performance breakdown. Anything not listed here just falls
# back to its raw node name, so new backend nodes never break the UI.
NODE_LABELS = {
    "router": "Route",
    "research": "Research",
    "orchestrator": "Plan",
    "worker": "Write sections",
    "reducer": "Finalize + images",
}
NODE_ORDER_HINT = ["router", "research", "orchestrator", "worker", "reducer"]

PAST_BLOGS_LIMIT = 50
LOG_TAIL = 80

# ------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------
st.set_page_config(page_title=APP_NAME, page_icon="\U0001f58b",
                   layout="wide", initial_sidebar_state="expanded")
styles.inject()

for key, default in (("last_out", None), ("last_timings", None), ("logs", []), ("topic_prefill", "")):
    st.session_state.setdefault(key, default)


# ------------------------------------------------------------------
# Sidebar: run controls + past blogs
# ------------------------------------------------------------------
sidebar_state = render_sidebar(
    app_name=APP_NAME,
    model_name=OLLAMA_MODEL,
    topic_prefill=st.session_state["topic_prefill"],
    past_blogs_limit=PAST_BLOGS_LIMIT,
)

if sidebar_state.clear_clicked:
    st.session_state["last_out"] = None
    st.session_state["last_timings"] = None
    st.session_state["logs"] = []
    st.session_state["topic_prefill"] = ""
    st.rerun()

if sidebar_state.load_clicked and sidebar_state.selected_path is not None:
    md_text = read_md_file(sidebar_state.selected_path)
    st.session_state["last_out"] = {
        "plan": None,
        "evidence": [],
        "image_specs": [],
        "final": md_text,
    }
    st.session_state["last_timings"] = None
    st.session_state["topic_prefill"] = extract_title_from_md(
        md_text, sidebar_state.selected_path.stem)
    st.rerun()


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
render_header(APP_TITLE, APP_TAGLINE, model_name=OLLAMA_MODEL)


# ------------------------------------------------------------------
# Revise an imported draft (main page, not the sidebar)
# ------------------------------------------------------------------
# Separate, much shorter path than the main "Generate blog" pipeline -
# no research/planning/fan-out, just the uploaded draft + instruction
# straight to pipeline.revise_draft(). Lands in the exact same
# session-state shape "load a saved post" uses above, so it renders
# through the normal Article/Export tabs with no extra plumbing.
#
# Hidden for the run where "Generate blog" was just clicked - once
# generation starts, this run's page should only show the running-agent
# status/progress up top, not an unrelated upload box sitting above it.
# It's back on the very next rerun since run_clicked resets to False.
if not sidebar_state.run_clicked:
    revise_state = render_revise_panel()

    if revise_state.revise_clicked:
        if revise_state.uploaded_draft is None:
            st.warning("Upload a draft before revising.")
            st.stop()
        if not revise_state.edit_instruction.strip():
            st.warning("Enter what you want changed before revising.")
            st.stop()

        try:
            draft_md = extract_draft_text(
                revise_state.uploaded_draft.name,
                revise_state.uploaded_draft.getvalue(),
            )
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

        if not draft_md.strip():
            st.warning("That file doesn't seem to have any text in it.")
            st.stop()

        with st.spinner("Revising your draft..."):
            try:
                revised_md = pipeline.revise_draft(
                    draft_md, revise_state.edit_instruction.strip())
            except Exception as exc:
                st.error(
                    "The revise call raised an error. This usually means Ollama isn't "
                    "running or the configured model isn't pulled locally."
                )
                with st.expander("Technical details"):
                    st.exception(exc)
                st.stop()

        revised_title = extract_title_from_md(
            revised_md, Path(revise_state.uploaded_draft.name).stem)
        revised_filename = f"{pipeline.safe_slug(revised_title)}_revised.md"
        Path(revised_filename).write_text(revised_md, encoding="utf-8")

        st.session_state["last_out"] = {
            "plan": None,
            "evidence": [],
            "image_specs": [],
            "final": revised_md,
            "repurposed_content": None,
        }
        st.session_state["last_timings"] = None
        st.session_state["topic_prefill"] = revised_title
        st.session_state["logs"].append(
            f"[{time.strftime('%H:%M:%S')}] Revised '{revise_state.uploaded_draft.name}' -> {revised_filename}"
        )
        st.toast("Draft revised.")
        st.rerun()


# ------------------------------------------------------------------
# Run the pipeline
# ------------------------------------------------------------------
if sidebar_state.run_clicked:
    if not sidebar_state.topic.strip():
        st.warning("Enter a topic before generating.")
        st.stop()

    inputs: Dict[str, Any] = {
        "topic": sidebar_state.topic.strip(),
        "desired_length": sidebar_state.length,
        "desired_tone": sidebar_state.tone,
        "desired_language": sidebar_state.language,
        "desired_audience": sidebar_state.audience,
        "desired_blog_kind": sidebar_state.blog_kind,
        "citation_mode": sidebar_state.citation_mode,
        "include_images": sidebar_state.include_images,
        "image_style": sidebar_state.image_style,
        "mode": "",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "as_of": sidebar_state.as_of.isoformat(),
        "recency_days": 7,
        "sections": [],
        "merged_md": "",
        "fact_check_findings": [],
        "critic_findings": [],
        "image_specs": [],
        "final": "",
        "repurposed_content": None,
    }

    status = st.status("Running the agent pipeline...", expanded=True)
    step_area = st.empty()
    draft_area = st.empty()
    draft_chunks: Dict[int, List[str]] = {}

    def _on_step(node_name: str, elapsed: float) -> None:
        status.write(
            f"**{NODE_LABELS.get(node_name, node_name)}** finished ({elapsed:.1f}s)")

    def _on_tick(order: List[str], timings: Dict[str, Dict[str, float]]) -> None:
        step_area.markdown(
            build_step_track_html(
                order, timings, NODE_LABELS, NODE_ORDER_HINT, still_running=True),
            unsafe_allow_html=True,
        )

    def _on_token(event: Dict[str, Any]) -> None:
        # Live section-drafting preview. backend/nodes/worker.py's
        # _draft_section emits one section_delta event per streamed
        # token/chunk while a worker call is running. Purely cosmetic -
        # if the installed LangGraph/model don't support custom-stream
        # events this just never fires and the rest of the run behaves
        # the same either way.
        if event.get("type") != "section_delta":
            return
        task_id = event.get("task_id", 0)
        draft_chunks.setdefault(task_id, []).append(event.get("delta", ""))
        preview = "\n\n---\n\n".join(
            f"Section {tid}\n{''.join(pieces)}" for tid, pieces in sorted(draft_chunks.items())
        )
        draft_area.markdown(
            f'<div class="bwa-card-flat"><div class="bwa-card-title">{_icon("zap")} Drafting live</div>'
            f'<div style="white-space:pre-wrap;font-size:0.83rem;max-height:280px;overflow-y:auto;">'
            f'{html.escape(preview)}</div></div>',
            unsafe_allow_html=True,
        )

    try:
        final_state, timing_summary = pipeline.run_pipeline(
            inputs, on_step=_on_step, on_tick=_on_tick, on_token=_on_token
        )
    except Exception as exc:
        status.update(label="Run failed", state="error", expanded=True)
        st.error(
            "The pipeline raised an error before finishing. This usually means Ollama "
            "isn't running, the configured model isn't pulled locally, or a research/"
            "image-generation call failed."
        )
        with st.expander("Technical details"):
            st.exception(exc)
        st.stop()

    # Freeze the tracker in its final state so untouched nodes read as
    # "skipped" instead of stuck on "pending".
    step_area.markdown(
        build_step_track_html(
            timing_summary["order"], timing_summary["by_node"], NODE_LABELS, NODE_ORDER_HINT,
            still_running=False,
        ),
        unsafe_allow_html=True,
    )

    draft_area.empty()
    status.update(label="Done", state="complete", expanded=False)
    st.session_state["last_out"] = final_state
    st.session_state["last_timings"] = timing_summary
    st.session_state["logs"].append(
        f"[{time.strftime('%H:%M:%S')}] Generated '{sidebar_state.topic.strip()}' in {timing_summary['total_seconds']:.1f}s"
    )
    st.toast("Blog generated.")


# ------------------------------------------------------------------
# Results
# ------------------------------------------------------------------
out = st.session_state["last_out"]
timing_summary = st.session_state["last_timings"]

if not out:
    empty_state(
        "No blog yet",
        "Enter a topic in the sidebar and click “Generate blog” to run the pipeline, "
        "reopen a saved post from the Saved Blogs list, or revise a draft above.",
        icon="sparkles",
    )
else:
    plan_obj = out.get("plan")
    if hasattr(plan_obj, "model_dump"):
        plan_dict = plan_obj.model_dump()
    elif isinstance(plan_obj, dict) and plan_obj:
        plan_dict = plan_obj
    else:
        plan_dict = {}

    blog_title = plan_dict.get("blog_title") or extract_title_from_md(
        out.get("final") or "", "Untitled post")
    final_md = out.get("final") or ""

    # ---- Headline badges ----
    pills = [badge(blog_title, tone="accent", icon="file-text")]
    if plan_dict.get("blog_kind"):
        pills.append(badge(plan_dict["blog_kind"], tone="muted"))
    if out.get("mode"):
        pills.append(badge(f'mode: {out["mode"]}', tone="muted"))
    st.markdown(f"<div>{''.join(pills)}</div>", unsafe_allow_html=True)
    st.write("")

    # ---- Pipeline progress (stays visible for the rest of the session) ----
    if timing_summary:
        card_open("Pipeline progress", icon="layers")
        st.markdown(
            build_step_track_html(
                timing_summary["order"], timing_summary["by_node"], NODE_LABELS, NODE_ORDER_HINT,
                still_running=False,
            ),
            unsafe_allow_html=True,
        )
        card_close()
    elif plan_dict == {} and not out.get("evidence"):
        st.markdown(
            f'<div class="bwa-saved-meta">{_icon("clock")} Reopened from disk — no run telemetry for this post.</div>',
            unsafe_allow_html=True,
        )
        st.write("")

    # ---- Headline metrics ----
    metric_cols = st.columns(5)
    metric_cols[0].metric("Sections", len(plan_dict.get("tasks", [])) or "-")
    metric_cols[1].metric("Evidence sources", len(out.get("evidence") or []))
    metric_cols[2].metric("Images planned", len(out.get("image_specs") or []))
    metric_cols[3].metric("Words", len(final_md.split()) if final_md else 0)
    metric_cols[4].metric(
        "Run time", f"{timing_summary['total_seconds']:.1f}s" if timing_summary else "-")

    st.write("")

    tab_article, tab_outline, tab_research, tab_images, tab_repurpose, tab_perf = st.tabs(
        ["Article", "Outline", "Research", "Images", "Repurpose", "Performance"]
    )

    # ---- Article tab (the generated blog, as a real reading page) ----
    with tab_article:
        render_article(final_md, evidence=out.get("evidence"))

        if final_md:
            st.write("")
            md_filename = f"{pipeline.safe_slug(blog_title)}.md"
            try:
                docx_bytes = markdown_to_docx_bytes(final_md)
            except Exception:
                docx_bytes = None
            download_cols = st.columns(3)
            download_cols[0].download_button(
                "Download Markdown",
                data=final_md.encode("utf-8"),
                file_name=md_filename,
                mime="text/markdown",
                width="stretch",
            )
            download_cols[1].download_button(
                "Download Word (.docx)",
                data=docx_bytes or b"",
                file_name=f"{pipeline.safe_slug(blog_title)}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
                disabled=docx_bytes is None,
                help=None if docx_bytes is not None else "Couldn't convert this post to Word -- Markdown download is still available.",
            )
            download_cols[2].download_button(
                "Download bundle (.md + images)",
                data=pipeline.bundle_zip(
                    final_md, md_filename, Path("images")),
                file_name=f"{pipeline.safe_slug(blog_title)}_bundle.zip",
                mime="application/zip",
                width="stretch",
            )

    # ---- Outline tab (used to just be called "Plan") ----
    with tab_outline:
        tasks = plan_dict.get("tasks", [])
        if not tasks:
            empty_state("No outline available",
                        "This post doesn't have a saved plan.", icon="list-tree", small=True)
        else:
            cols = st.columns(3)
            cols[0].write(f"**Audience**  \n{plan_dict.get('audience', '-')}")
            cols[1].write(f"**Tone**  \n{plan_dict.get('tone', '-')}")
            cols[2].write(f"**Kind**  \n{plan_dict.get('blog_kind', '-')}")

            df = pd.DataFrame(
                [
                    {
                        "#": t.get("id"),
                        "Section": t.get("title"),
                        "Words": t.get("target_words"),
                        "Research": "Yes" if t.get("requires_research") else "",
                        "Citations": "Yes" if t.get("requires_citations") else "",
                        "Code": "Yes" if t.get("requires_code") else "",
                        "Tags": ", ".join(t.get("tags") or []),
                    }
                    for t in tasks
                ]
            ).sort_values("#")
            st.dataframe(df, width="stretch", hide_index=True)

            with st.expander("Full task details (JSON)"):
                st.json(tasks)

            # ---- Regenerate a single section ----
            # Redrafts one section with the exact same prompt/grounding
            # rules as the original run (worker.py's regenerate_section),
            # then splices it back in place - everything else (other
            # sections, already-placed images) stays untouched.
            st.divider()
            section_label("Regenerate a section", icon="zap")
            tasks_sorted = sorted(tasks, key=lambda t: t.get("id", 0))
            task_labels = [
                f"{t.get('id')}. {t.get('title')}" for t in tasks_sorted]
            regen_cols = st.columns([3, 1])
            selected_label = regen_cols[0].selectbox(
                "Section to regenerate", task_labels, label_visibility="collapsed",
            )
            regen_clicked = regen_cols[1].button("Regenerate", width="stretch")

            if regen_clicked:
                selected_task = tasks_sorted[task_labels.index(selected_label)]
                section_index = tasks_sorted.index(selected_task)
                evidence_dicts = [
                    e.model_dump() if hasattr(e, "model_dump") else e
                    for e in (out.get("evidence") or [])
                ]
                with st.spinner(f"Redrafting “{selected_task.get('title')}”..."):
                    try:
                        new_section_md = pipeline.regenerate_section(
                            task=selected_task,
                            topic=out.get(
                                "topic", sidebar_state.topic.strip()),
                            mode=out.get("mode", ""),
                            as_of=out.get("as_of", ""),
                            recency_days=out.get("recency_days", 7),
                            plan=plan_dict,
                            evidence=evidence_dicts,
                            language=out.get("desired_language", ""),
                        )
                    except Exception as exc:
                        st.error("Couldn't regenerate this section.")
                        with st.expander("Technical details"):
                            st.exception(exc)
                    else:
                        out["final"] = pipeline.splice_section(
                            final_md, section_index, new_section_md)
                        st.session_state["last_out"] = out
                        st.success(
                            f"Regenerated “{selected_task.get('title')}”.")
                        st.rerun()

    # ---- Research tab (used to just be called "Evidence") ----
    with tab_research:
        evidence = out.get("evidence") or []
        if not evidence:
            empty_state(
                "No evidence retrieved",
                "This post ran in closed-book mode, or no Tavily results came back.",
                icon="search",
                small=True,
            )
        else:
            rows = [e.model_dump() if hasattr(e, "model_dump")
                    else e for e in evidence]
            st.dataframe(
                pd.DataFrame(rows)[["title", "published_at", "source", "url"]],
                width="stretch",
                hide_index=True,
            )

        # ---- Fact-check findings (backend/reducer/fact_check.py) ----
        findings = out.get("fact_check_findings") or []
        if findings:
            st.write("")
            section_label("Fact-check findings", icon="alert-triangle")
            st.caption(
                "A conservative pass flagging specific, checkable claims the draft "
                "makes that the retrieved evidence doesn't clearly support. Review, "
                "don't assume -- this is a second opinion, not ground truth."
            )
            st.dataframe(
                pd.DataFrame(findings)[["section_title", "claim", "concern"]],
                width="stretch",
                hide_index=True,
            )

        # ---- Critic findings (backend/reducer/critic.py) ----
        critic_findings = out.get("critic_findings") or []
        if critic_findings:
            st.write("")
            section_label("Critical review", icon="alert-triangle")
            st.caption(
                "An adversarial editing pass arguing against the draft's reasoning -- "
                "overgeneralizations, unsupported claims, and logical gaps, evidence or "
                "not. Also a second opinion, not ground truth."
            )
            st.dataframe(
                pd.DataFrame(critic_findings)[
                    ["section_title", "issue_type", "critique", "suggestion"]],
                width="stretch",
                hide_index=True,
            )

    # ---- Images tab ----
    with tab_images:
        specs = out.get("image_specs") or []
        images_dir = Path("images")
        image_files = [p for p in images_dir.iterdir(
        ) if p.is_file()] if images_dir.is_dir() else []

        if not specs and not image_files:
            empty_state("No images planned",
                        "This post didn't call for any illustrations.", icon="image", small=True)
        else:
            if specs:
                with st.expander(f"Image plan ({len(specs)})", expanded=False):
                    st.json(specs)

            if image_files:
                image_cols = st.columns(min(3, len(image_files)) or 1)
                for i, path in enumerate(sorted(image_files)):
                    with image_cols[i % len(image_cols)]:
                        st.image(str(path), caption=path.name, width="stretch")

                zip_bytes = pipeline.images_zip(images_dir)
                if zip_bytes:
                    st.download_button(
                        "Download images (.zip)",
                        data=zip_bytes,
                        file_name="images.zip",
                        mime="application/zip",
                    )
            else:
                empty_state(
                    "Images planned, not yet generated",
                    "The plan calls for illustrations, but none exist in the images/ folder on disk yet. "
                    "If a run already finished, check the Article tab for an “image could not be "
                    "generated” note explaining why.",
                    icon="image",
                    small=True,
                )

    # ---- Repurpose tab (backend/reducer/repurpose.py) ----
    with tab_repurpose:
        repurposed = out.get("repurposed_content")
        if not repurposed:
            empty_state(
                "No repurposed copy yet",
                "This shows up automatically once a post finishes generating -- a Twitter/X "
                "thread, a LinkedIn post, and a newsletter blurb built from the finished article.",
                icon="sparkles",
                small=True,
            )
        else:
            section_label("Twitter / X thread", icon="sparkles")
            thread = repurposed.get("twitter_thread") or []
            if thread:
                thread_text = "\n\n".join(
                    f"{i}/ {tweet}" for i, tweet in enumerate(thread, start=1))
                st.code(thread_text, language=None)
                st.caption(f"{len(thread)} tweets")
            else:
                st.caption("No thread generated for this post.")

            st.write("")
            section_label("LinkedIn post", icon="sparkles")
            linkedin_post = repurposed.get("linkedin_post") or ""
            if linkedin_post:
                st.code(linkedin_post, language=None)
            else:
                st.caption("No LinkedIn post generated for this post.")

            st.write("")
            section_label("Newsletter blurb", icon="sparkles")
            newsletter_blurb = repurposed.get("newsletter_blurb") or ""
            if newsletter_blurb:
                st.code(newsletter_blurb, language=None)
            else:
                st.caption("No newsletter blurb generated for this post.")

            if thread or linkedin_post or newsletter_blurb:
                st.write("")
                bundle_text = (
                    "=== TWITTER / X THREAD ===\n\n"
                    + "\n\n".join(f"{i}/ {tweet}" for i,
                                  tweet in enumerate(thread, start=1))
                    + "\n\n=== LINKEDIN POST ===\n\n"
                    + linkedin_post
                    + "\n\n=== NEWSLETTER BLURB ===\n\n"
                    + newsletter_blurb
                )
                st.download_button(
                    "Download all repurposed copy (.txt)",
                    data=bundle_text.encode("utf-8"),
                    file_name=f"{pipeline.safe_slug(blog_title)}_repurposed.txt",
                    mime="text/plain",
                )

    # ---- Performance tab ----
    with tab_perf:
        if not timing_summary:
            empty_state(
                "No telemetry for this post",
                "Timing is only captured for posts generated in this session, not for reopened past posts.",
                icon="bar-chart",
                small=True,
            )
        else:
            total_seconds = timing_summary["total_seconds"]
            words_per_sec = (len(final_md.split()) /
                             total_seconds) if total_seconds else 0.0

            perf_cols = st.columns(3)
            perf_cols[0].metric("Total run time", f"{total_seconds:.1f}s")
            perf_cols[1].metric("Throughput", f"{words_per_sec:.1f} words/s")
            perf_cols[2].metric("Model", OLLAMA_MODEL)

            timing_rows = [
                {
                    "Stage": NODE_LABELS.get(name, name),
                    "Calls": info["count"],
                    "Total seconds": round(info["total"], 2),
                    "Avg seconds/call": round(info["total"] / info["count"], 2),
                    "Share of run": f"{(info['total'] / total_seconds * 100):.0f}%" if total_seconds else "-",
                }
                for name, info in (
                    (n, timing_summary["by_node"][n]) for n in timing_summary["order"]
                )
            ]
            if timing_rows:
                st.dataframe(pd.DataFrame(timing_rows),
                             width="stretch", hide_index=True)
                st.bar_chart(
                    pd.DataFrame(timing_rows).set_index(
                        "Stage")["Total seconds"],
                    width="stretch",
                )

            with st.expander("What affects performance here"):
                st.markdown(
                    "- **Plan (\"orchestrator\")** and **Route** are single sequential LLM calls; "
                    "they run before any writing starts, so they set a floor on latency.\n"
                    "- **Write sections** runs one call per section. The graph fans these out in "
                    "parallel, but a single local Ollama server typically serves one generation "
                    "at a time, so wall-clock time here scales with section count on most setups.\n"
                    "- **Finalize + images** includes merging sections, the image-placement "
                    "decision call, and any image generation calls, which may hit an external API "
                    "and add network latency.\n"
                    "- Structured-output calls (router, evidence extraction, planning) occasionally "
                    "need a retry on local models if a response doesn't validate against its schema; "
                    "that isn't currently instrumented separately from its node's time above."
                )

            with st.expander("Event log"):
                st.text_area(
                    "Event log",
                    value="\n".join(st.session_state["logs"][-LOG_TAIL:]),
                    height=240,
                    label_visibility="collapsed",
                )
