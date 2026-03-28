from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ThreadState:
    thread_key: str
    workspace_root: str
    thread_name: str | None
    claude_session_id: str | None
    created_at: str
    last_used_at: str
    last_status: str
    bridge_version: str
    claude_version: str | None
    last_error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThreadState":
        return cls(**data)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    thread_key: str
    started_at: str
    ended_at: str
    duration_ms: int
    used_resume: bool
    prompt_sha256: str
    exit_code: int
    parse_ok: bool
    stdout_preview: str
    stderr_preview: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
