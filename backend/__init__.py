"""Backend package for the blog writing agent.

Pipeline: router -> (research if needed) -> orchestrator -> workers
(one per outline section, run in parallel) -> reducer (merge -> fact
check -> critic -> images -> repurpose).

Layout:
    config.py          env vars + tunables (model name, api keys, limits)
    logging_utils.py    shared logger factory
    schemas.py          pydantic models used across the graph
    state.py            the State TypedDict
    llm_client.py        shared ChatOllama instance
    nodes/               router, research, orchestrator, worker
    reducer/             merge, fact_check, critic, images, repurpose
    graph.py             builds + compiles the graph into `app`

bwa_backend.py at the project root just re-exports app / OLLAMA_MODEL /
State / regenerate_section so the frontend doesn't need new imports.
"""
