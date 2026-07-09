"""Filesystem helpers for the "Saved Blogs" list.

Just reads .md files out of the working directory - no backend calls,
nothing fancy.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List


def list_past_blogs() -> List[Path]:
    """Returns .md files in the working directory, newest first."""
    files = [p for p in Path(".").glob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def read_md_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_title_from_md(md: str, fallback: str) -> str:
    """Uses the first '# ' heading as the title, if there is one."""
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def relative_time(mtime: float) -> str:
    """'3h ago' / '2d ago' style label for a post's last-modified time.
    Just cosmetic, doesn't affect sort order or which file loads."""
    delta = max(0, time.time() - mtime)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def build_label_map(paths: List[Path]) -> Dict[str, Path]:
    """Builds the {label: path} map for the "reopen a post" selectbox."""
    file_by_label: Dict[str, Path] = {}
    for path in paths:
        try:
            title = extract_title_from_md(read_md_file(path), path.stem)
        except OSError:
            title = path.stem
        label = f"{title} ({path.name})"
        file_by_label[label] = path
    return file_by_label
