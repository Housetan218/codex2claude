from __future__ import annotations

import json
from pathlib import Path

from .errors import StateCorruptionError
from .models import RunRecord, ThreadState


def save_thread_state(path: Path, state: ThreadState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def load_thread_state(path: Path) -> ThreadState:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateCorruptionError(f"invalid thread state: {path}") from exc
    try:
        return ThreadState.from_dict(data)
    except (TypeError, ValueError) as exc:
        raise StateCorruptionError(f"invalid thread state shape: {path}") from exc


def save_run_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)
