"""Backward-compatible entry point for the backend.

Used to be one ~590-line file with every schema, node, and the graph
itself in it. Now it's the backend/ package (config, schemas, state,
llm_client, nodes/, reducer/, graph.py - see backend/__init__.py for the
full layout). This file just re-exports the same stuff as before so
pipeline.py and bwa_frontend.py don't need any import changes:

    from bwa_backend import app
    from bwa_backend import OLLAMA_MODEL
"""
from __future__ import annotations

from backend.config import OLLAMA_MODEL
from backend.graph import app
from backend.nodes.worker import regenerate_section
from backend.revise import revise_draft
from backend.state import State

__all__ = ["app", "OLLAMA_MODEL", "State", "regenerate_section", "revise_draft"]
