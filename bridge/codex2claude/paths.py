from __future__ import annotations

import os
from pathlib import Path


def bridge_root() -> Path:
    override = os.environ.get("CODEX2CLAUDE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "codex2claude"


def threads_dir() -> Path:
    return bridge_root() / "threads"


def runs_dir() -> Path:
    return bridge_root() / "runs"


def logs_dir() -> Path:
    return bridge_root() / "logs"


def thread_file_path(thread_key: str) -> Path:
    return threads_dir() / f"{thread_key}.json"


def thread_lock_path(thread_key: str) -> Path:
    return threads_dir() / f"{thread_key}.lock"


def run_dir_path(thread_key: str) -> Path:
    return runs_dir() / thread_key
