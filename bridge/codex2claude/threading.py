from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_workspace_root(workspace_root: str) -> str:
    return str(Path(workspace_root).expanduser().resolve())


def make_thread_key(workspace_root: str, thread_name: str | None) -> str:
    canonical_root = canonical_workspace_root(workspace_root)
    raw = f"codex-to-claude::{canonical_root}::{thread_name or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
