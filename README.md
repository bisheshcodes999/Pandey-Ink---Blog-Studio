# PandeyInk — Blog Studio

A local, multi-agent blog-writing pipeline: give it a topic, and it researches, plans, drafts, fact-checks, illustrates, and repurposes a full technical blog post — running entirely on your own machine via [Ollama](https://ollama.com) and local Stable Diffusion, no API billing required.

Built with [LangGraph](https://github.com/langchain-ai/langgraph) for the multi-agent orchestration and [Streamlit](https://streamlit.io) for the UI.

## Why this exists

Asking a chatbot for a blog post gives you one pass of one model's best guess. This does more of what an actual editorial process looks like:

- **Live research** when the topic calls for it (Tavily web search), with a router that decides per-topic whether research is even needed.
- **A real outline first** — audience, structure, and section-by-section word targets — before any prose gets written.
- **Parallel section drafting**, each section grounded only in the context it needs.
- **A fact-check pass** that flags claims the retrieved evidence doesn't actually support, and a separate **adversarial critic pass** that argues against the draft's reasoning even when there's no source to check against.
- **Inline illustrations**, generated locally and spliced deterministically into the section they belong to — not a separate downloadable gallery.
- **Repurposing** the finished post into a Twitter/X thread, a LinkedIn post, and a newsletter blurb automatically.

## Pipeline

```
router → (research?) → orchestrator → [worker, worker, ...] → reducer
```

`reducer` is itself a subgraph:

```
merge_content → fact_check → critic → decide_images → generate_and_place_images → repurpose
```

| Stage | What it does |
|---|---|
| **Router** | Classifies the topic as closed_book (evergreen), hybrid, or open_book (news/volatile), and generates search queries if research is needed. |
| **Research** | Runs Tavily searches, normalizes results into evidence sources, drops down to closed_book if nothing real comes back. |
| **Orchestrator** | Builds the outline — title, audience, tone, structure, and a section list with word targets — folding in every sidebar control (Length, Tone, Audience, Structure, Citations). |
| **Workers** | One parallel call per outline section. |
| **Merge** | Stitches sections back together in outline order. |
| **Fact-check** | Flags claims the draft makes that the evidence doesn't clearly support. |
| **Critic** | Adversarial pass — overgeneralizations, logical gaps, weak evidence — runs even with no sources to check against. |
| **Images** | Decides which sections deserve an illustration, generates them locally (Stable Diffusion, CPU), and splices each one directly under its section's heading. |
| **Repurpose** | Turns the finished post into a Twitter/X thread, LinkedIn post, and newsletter blurb. |

## Setup

**1. Install [Ollama](https://ollama.com) and pull a model:**

```
ollama pull qwen3:8b
```

**2. Create a virtual environment and install dependencies:**

```
python -m venv venv
venv\Scripts\activate          (Windows)
source venv/bin/activate       (macOS/Linux)

pip install -r requirements.txt
```

**3. Set up your environment file:**

```
copy .env.example .env         (Windows)
cp .env.example .env           (macOS/Linux)
```

Fill in `TAVILY_API_KEY` (optional — research is skipped without it) and confirm `OLLAMA_MODEL` matches the model you pulled.

**4. Run it:**

```
venv\Scripts\streamlit run bwa_frontend.py
```

The first "Generate blog" run with images enabled downloads the local image model (~2-3GB, one-time) from Hugging Face.

## Project structure

```
backend/
  config.py          tunable constants + sidebar option -> prompt-instruction maps
  schemas.py          Pydantic schemas every structured LLM call is validated against
  state.py             LangGraph shared state
  graph.py              builds + compiles the pipeline
  llm_client.py     shared Ollama client
  local_image_gen.py  local Stable Diffusion (sd-turbo) generation
  revise.py             standalone "revise my draft" call, outside the graph
  nodes/               router, research, orchestrator, worker
  reducer/             merge, fact_check, critic, images, repurpose
ui/
  styles.py, icons.py, components.py     design system
  sidebar.py, header.py, revise_panel.py, blog_viewer.py, progress_panel.py    panels
  docx_export.py, docx_import.py             Markdown <-> Word conversion
  saved_posts.py                                   past-posts list
bwa_frontend.py     Streamlit entry point
pipeline.py             graph streaming + timing, wraps backend/graph.py for the UI
tests/                     unit tests for pure logic (no model/API needed to run)
```

## Testing

The pure string-manipulation logic (image placement, slug generation) is unit-tested independently of the model stack:

```
python -m unittest tests.test_image_placement -v
``` 

## Notes

- Local image generation uses `stabilityai/sd-turbo`, which ships under Stability AI's **non-commercial research license**. Fine for personal/local use; check the license before using generated images commercially.
- `requirements.txt` is the curated install list; `requirements.lock.txt` pins the exact versions this project was last verified against, if you need to reproduce that environment precisely.
- Everything runs locally — no API billing for text generation, research (beyond Tavily's free tier), or images.
