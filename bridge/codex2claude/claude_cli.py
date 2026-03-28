from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from .errors import ClaudeInvocationError, ClaudeTimeoutError, StateCorruptionError


@dataclass(slots=True)
class ClaudeResult:
    session_id: str | None
    result_text: str
    model_name: str | None
    raw_payload: dict[str, object]
    stderr_text: str


def build_claude_command(prompt: str, session_id: str | None, claude_bin: str = "claude") -> list[str]:
    command = [claude_bin]
    if session_id:
        command.extend(["--resume", session_id])
    command.extend(["-p", prompt, "--output-format", "json"])
    return command


def parse_claude_response(stdout: str, stderr: str = "") -> ClaudeResult:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise StateCorruptionError("Claude returned malformed JSON") from exc

    result_text = payload.get("result")
    if not isinstance(result_text, str):
        raise StateCorruptionError("Claude JSON missing string result")

    if payload.get("is_error") is True:
        raise ClaudeInvocationError(result_text)

    session_id = payload.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        raise StateCorruptionError("Claude JSON returned invalid session_id")
    if isinstance(session_id, str) and not session_id:
        raise StateCorruptionError("Claude JSON returned empty session_id")

    model_name = _extract_model_name(payload)

    return ClaudeResult(
        session_id=session_id,
        result_text=result_text,
        model_name=model_name,
        raw_payload=payload,
        stderr_text=stderr,
    )


def _extract_model_name(payload: dict[str, object]) -> str | None:
    direct_model = payload.get("model")
    if isinstance(direct_model, str) and direct_model:
        return direct_model

    direct_model_name = payload.get("model_name")
    if isinstance(direct_model_name, str) and direct_model_name:
        return direct_model_name

    model_usage = payload.get("modelUsage")
    if isinstance(model_usage, dict):
        model_keys = [key for key in model_usage if isinstance(key, str) and key]
        if model_keys:
            return next(iter(model_keys))

    return None


def invoke_claude(
    prompt: str,
    session_id: str | None,
    timeout_seconds: int,
    cwd: str | None = None,
    claude_bin: str = "claude",
) -> ClaudeResult:
    command = build_claude_command(prompt=prompt, session_id=session_id, claude_bin=claude_bin)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
        )
    except FileNotFoundError as exc:
        raise ClaudeInvocationError(f"Claude CLI not found: {claude_bin}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClaudeTimeoutError(f"Claude timed out after {timeout_seconds}s") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown Claude failure"
        raise ClaudeInvocationError(stderr)

    return parse_claude_response(completed.stdout, completed.stderr)


def read_claude_version(claude_bin: str = "claude") -> str | None:
    try:
        completed = subprocess.run(
            [claude_bin, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    version = completed.stdout.strip() or completed.stderr.strip()
    return version or None
