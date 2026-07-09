"""One shared ChatOllama client - every node builds its calls from this."""
from __future__ import annotations

from langchain_ollama import ChatOllama

from backend.config import OLLAMA_MODEL

llm = ChatOllama(model=OLLAMA_MODEL)
