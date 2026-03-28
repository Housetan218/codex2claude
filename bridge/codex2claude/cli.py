from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

from .claude_cli import invoke_claude, read_claude_version
from .errors import (
    EXIT_CLAUDE_ERROR,
    EXIT_OK,
    BridgeError,
    InvalidArgumentsError,
)
from .locking import acquire_thread_lock
from .logging_utils import append_bridge_log, utc_now
from .models import RunRecord, ThreadState
from .paths import logs_dir, run_dir_path, thread_file_path, thread_lock_path, threads_dir
from .state import load_thread_state, save_run_record, save_thread_state
from .threading import canonical_workspace_root, make_thread_key
from .version import __version__


DEFAULT_TIMEOUT_SECONDS = 300


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex2claude")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask")
    ask.add_argument("--prompt", required=True)
    ask.add_argument("--workspace")
    ask.add_argument("--thread")
    ask.add_argument("--new", action="store_true")
    ask.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)

    status = subparsers.add_parser("status")
    status.add_argument("--workspace")
    status.add_argument("--thread")

    forget = subparsers.add_parser("forget")
    forget.add_argument("--workspace")
    forget.add_argument("--thread")

    gc = subparsers.add_parser("gc")
    gc.add_argument("--max-age-days", type=int, default=7)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--workspace")
    doctor.add_argument("--thread")
    return parser


def _resolve_workspace_root(workspace: str | None) -> str:
    return canonical_workspace_root(workspace or ".")


def _thread_key(workspace: str | None, thread_name: str | None) -> tuple[str, str]:
    workspace_root = _resolve_workspace_root(workspace)
    return workspace_root, make_thread_key(workspace_root, thread_name)


def _read_optional_thread_state(path: Path) -> ThreadState | None:
    if not path.exists():
        return None
    try:
        return load_thread_state(path)
    except BridgeError:
        path.unlink(missing_ok=True)
        return None


def _write_run_record(thread_key: str, prompt: str, start_time: str, duration_ms: int, used_resume: bool, exit_code: int, parse_ok: bool, stdout_preview: str, stderr_preview: str) -> None:
    run_id = uuid.uuid4().hex
    record = RunRecord(
        run_id=run_id,
        thread_key=thread_key,
        started_at=start_time,
        ended_at=utc_now(),
        duration_ms=duration_ms,
        used_resume=used_resume,
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        exit_code=exit_code,
        parse_ok=parse_ok,
        stdout_preview=stdout_preview[:200],
        stderr_preview=stderr_preview[:200],
    )
    run_path = run_dir_path(thread_key) / f"{record.ended_at.replace(':', '-')}-{run_id}.json"
    save_run_record(run_path, record)


def _handle_ask(args: argparse.Namespace) -> int:
    workspace_root, thread_key = _thread_key(args.workspace, args.thread)
    state_path = thread_file_path(thread_key)
    lock_path = thread_lock_path(thread_key)
    claude_bin = os.environ.get("CODEX2CLAUDE_CLAUDE_BIN", "claude")
    start_time = utc_now()
    started_at_monotonic = time.monotonic()

    with acquire_thread_lock(lock_path):
        prior_state = None if args.new else _read_optional_thread_state(state_path)
        used_resume = prior_state is not None and prior_state.claude_session_id is not None
        result = invoke_claude(
            prompt=args.prompt,
            session_id=prior_state.claude_session_id if used_resume else None,
            timeout_seconds=args.timeout,
            cwd=workspace_root,
            claude_bin=claude_bin,
        )
        now = utc_now()
        state = ThreadState(
            thread_key=thread_key,
            workspace_root=workspace_root,
            thread_name=args.thread,
            claude_session_id=result.session_id,
            created_at=prior_state.created_at if prior_state else now,
            last_used_at=now,
            last_status="ok",
            bridge_version=__version__,
            claude_version=read_claude_version(claude_bin) or (prior_state.claude_version if prior_state else None),
            last_error=None,
        )
        save_thread_state(state_path, state)
        _write_run_record(
            thread_key=thread_key,
            prompt=args.prompt,
            start_time=start_time,
            duration_ms=max(1, int((time.monotonic() - started_at_monotonic) * 1000)),
            used_resume=used_resume,
            exit_code=EXIT_OK,
            parse_ok=True,
            stdout_preview=result.result_text,
            stderr_preview=result.stderr_text,
        )
        append_bridge_log({"action": "ask", "outcome": "success", "thread_key": thread_key, "used_resume": used_resume})
        sys.stdout.write(result.result_text)
    return EXIT_OK


def _handle_status(args: argparse.Namespace) -> int:
    _, thread_key = _thread_key(args.workspace, args.thread)
    state_path = thread_file_path(thread_key)
    if not state_path.exists():
        sys.stderr.write(f"No thread state found for {thread_key}\n")
        return EXIT_CLAUDE_ERROR
    state = load_thread_state(state_path)
    sys.stdout.write(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n")
    return EXIT_OK


def _handle_forget(args: argparse.Namespace) -> int:
    _, thread_key = _thread_key(args.workspace, args.thread)
    state_path = thread_file_path(thread_key)
    if state_path.exists():
        state_path.unlink()
    lock_path = thread_lock_path(thread_key)
    if lock_path.exists():
        lock_path.unlink(missing_ok=True)
    append_bridge_log({"action": "forget", "outcome": "success", "thread_key": thread_key})
    return EXIT_OK


def _handle_gc(args: argparse.Namespace) -> int:
    threads_dir().mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - (args.max_age_days * 24 * 60 * 60)
    deleted = 0
    locked_thread_keys: set[str] = set()
    for lock_path in threads_dir().glob("*.lock"):
        thread_key = lock_path.stem
        try:
            with lock_path.open("a+", encoding="utf-8") as handle:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    locked_thread_keys.add(thread_key)
                    continue
                finally:
                    try:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
        except FileNotFoundError:
            continue
    for path in threads_dir().glob("*"):
        try:
            if path.stem in locked_thread_keys:
                continue
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except FileNotFoundError:
            continue
    runs_root = run_dir_path("placeholder").parent
    if runs_root.exists():
        for run_dir in runs_root.iterdir():
            try:
                if not run_dir.is_dir():
                    continue
                if run_dir.name in locked_thread_keys:
                    continue
                newest_mtime = max((child.stat().st_mtime for child in run_dir.rglob("*")), default=run_dir.stat().st_mtime)
                if newest_mtime >= cutoff:
                    continue
                for child in sorted(run_dir.rglob("*"), reverse=True):
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                run_dir.rmdir()
                deleted += 1
            except FileNotFoundError:
                continue
    append_bridge_log({"action": "gc", "outcome": "success", "deleted": deleted})
    return EXIT_OK


def _handle_doctor(args: argparse.Namespace) -> int:
    workspace_root, thread_key = _thread_key(args.workspace, args.thread)
    state_path = thread_file_path(thread_key)
    claude_bin = os.environ.get("CODEX2CLAUDE_CLAUDE_BIN", "claude")
    claude_version = read_claude_version(claude_bin)

    thread_state_payload: dict[str, object]
    if not state_path.exists():
        thread_state_payload = {
            "status": "missing",
            "path": str(state_path),
            "thread_key": thread_key,
        }
    else:
        try:
            state = load_thread_state(state_path)
            thread_state_payload = {
                "status": "ok",
                "path": str(state_path),
                "thread_key": thread_key,
                "session_id": state.claude_session_id,
                "last_status": state.last_status,
                "last_used_at": state.last_used_at,
            }
        except BridgeError as exc:
            thread_state_payload = {
                "status": "error",
                "path": str(state_path),
                "thread_key": thread_key,
                "message": str(exc),
            }

    payload = {
        "ok": claude_version is not None and thread_state_payload["status"] != "error",
        "bridge_version": __version__,
        "workspace_root": workspace_root,
        "bridge_root": {
            "status": "ok",
            "path": str(threads_dir().parent),
        },
        "paths": {
            "threads": str(threads_dir()),
            "logs": str(logs_dir()),
            "state_file": str(state_path),
        },
        "claude": {
            "status": "ok" if claude_version is not None else "error",
            "bin": claude_bin,
            "version": claude_version,
        },
        "thread_state": thread_state_payload,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return EXIT_OK if payload["ok"] else EXIT_CLAUDE_ERROR

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "ask":
            return _handle_ask(args)
        if args.command == "status":
            return _handle_status(args)
        if args.command == "forget":
            return _handle_forget(args)
        if args.command == "gc":
            return _handle_gc(args)
        if args.command == "doctor":
            return _handle_doctor(args)
        raise InvalidArgumentsError(f"Unknown command: {args.command}")
    except BridgeError as exc:
        append_bridge_log({"action": "error", "outcome": type(exc).__name__, "message": str(exc)})
        sys.stderr.write(f"{exc}\n")
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - last-resort guardrail
        append_bridge_log({"action": "error", "outcome": type(exc).__name__, "message": str(exc)})
        sys.stderr.write(f"{exc}\n")
        return EXIT_CLAUDE_ERROR
