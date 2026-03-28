# Codex-to-Claude v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stable one-way `Codex -> Claude` local integration consisting of a thin Codex skill entrypoint and a reusable Python 3 bridge that manages Claude sessions, persistence, locking, timeouts, logging, and recoverable failure handling.

**Architecture:** The Codex skill is a thin wrapper over a Python bridge CLI. The bridge stores one local thread record per workspace/thread key, persists Claude `session_id`, uses native `claude --resume` for follow-ups, and enforces deterministic per-thread locking and error mapping.

**Tech Stack:** Python 3 standard library, Claude CLI, Codex skill files, JSON state files, POSIX `fcntl` locking on macOS.

---

### Task 1: Create The Project Skeleton

**Files:**
- Create: `bridge/codex2claude/__init__.py`
- Create: `bridge/codex2claude/__main__.py`
- Create: `bridge/codex2claude/cli.py`
- Create: `bridge/codex2claude/paths.py`
- Create: `bridge/codex2claude/models.py`
- Create: `bridge/codex2claude/errors.py`
- Create: `bridge/codex2claude/version.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.version import __version__


def test_version_is_defined() -> None:
    assert isinstance(__version__, str)
    assert __version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cli_smoke.py -q`
Expected: FAIL because package files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create the package skeleton and define `__version__ = "0.1.0"` in `bridge/codex2claude/version.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_cli_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude tests/test_cli_smoke.py
git commit -m "feat: scaffold codex2claude bridge package"
```

### Task 2: Implement Path And State Models

**Files:**
- Modify: `bridge/codex2claude/paths.py`
- Modify: `bridge/codex2claude/models.py`
- Create: `tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.paths import bridge_root, thread_file_path


def test_thread_file_path_uses_bridge_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    path = thread_file_path("abc123")
    assert "codex2claude" in str(path)
    assert path.name == "abc123.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_paths.py -q`
Expected: FAIL because path helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement helpers for:

- bridge root
- threads directory
- runs directory
- logs directory
- thread file path
- run directory path

Define typed dataclasses for persisted thread state and run records.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_paths.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/paths.py bridge/codex2claude/models.py tests/test_paths.py
git commit -m "feat: add bridge paths and state models"
```

### Task 3: Add Thread Key Generation

**Files:**
- Modify: `bridge/codex2claude/cli.py`
- Create: `bridge/codex2claude/threading.py`
- Create: `tests/test_threading.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.threading import make_thread_key


def test_thread_key_is_stable_for_same_workspace_and_name() -> None:
    a = make_thread_key("/tmp/project", None)
    b = make_thread_key("/tmp/project", None)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_threading.py -q`
Expected: FAIL because thread key helper does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement canonical workspace normalization and deterministic thread key generation based on:

- workspace root
- bridge mode namespace
- optional thread name

Use SHA-256 and keep a readable prefix in filenames only if it does not reduce determinism.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_threading.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/threading.py bridge/codex2claude/cli.py tests/test_threading.py
git commit -m "feat: add deterministic bridge thread keys"
```

### Task 4: Implement JSON State Persistence

**Files:**
- Create: `bridge/codex2claude/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.models import ThreadState
from codex2claude.state import save_thread_state, load_thread_state


def test_save_and_load_thread_state(tmp_path) -> None:
    path = tmp_path / "thread.json"
    state = ThreadState(
        thread_key="abc",
        workspace_root="/tmp/project",
        thread_name=None,
        claude_session_id=None,
        created_at="2026-03-28T00:00:00Z",
        last_used_at="2026-03-28T00:00:00Z",
        last_status="new",
        bridge_version="0.1.0",
        claude_version=None,
        last_error=None,
    )
    save_thread_state(path, state)
    loaded = load_thread_state(path)
    assert loaded.thread_key == "abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_state.py -q`
Expected: FAIL because persistence helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- atomic JSON write
- thread state load/save
- run record write
- corruption detection with explicit exceptions

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_state.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/state.py tests/test_state.py
git commit -m "feat: add bridge state persistence"
```

### Task 5: Implement File Locking

**Files:**
- Create: `bridge/codex2claude/locking.py`
- Create: `tests/test_locking.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib
import pytest

from codex2claude.locking import acquire_thread_lock, LockConflictError


def test_second_lock_attempt_fails(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "thread.lock"
    with acquire_thread_lock(path):
        with pytest.raises(LockConflictError):
            with acquire_thread_lock(path):
                pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_locking.py -q`
Expected: FAIL because locking helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement a context manager backed by `fcntl.flock()` with non-blocking exclusive lock semantics.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_locking.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/locking.py tests/test_locking.py
git commit -m "feat: add per-thread file locking"
```

### Task 6: Implement Claude CLI Invocation

**Files:**
- Create: `bridge/codex2claude/claude_cli.py`
- Create: `tests/test_claude_cli_mock.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.claude_cli import build_claude_command


def test_build_claude_command_for_new_prompt() -> None:
    cmd = build_claude_command(prompt="hello", session_id=None)
    assert cmd[:2] == ["claude", "-p"]
    assert "--output-format" in cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_claude_cli_mock.py -q`
Expected: FAIL because Claude CLI wrapper does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement helpers to:

- build new-session command
- build resume command
- run subprocess with timeout
- parse Claude JSON envelope
- return normalized result object

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_claude_cli_mock.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/claude_cli.py tests/test_claude_cli_mock.py
git commit -m "feat: add Claude CLI bridge adapter"
```

### Task 7: Implement Ask Flow

**Files:**
- Modify: `bridge/codex2claude/cli.py`
- Modify: `bridge/codex2claude/state.py`
- Modify: `bridge/codex2claude/claude_cli.py`
- Create: `tests/test_ask_flow_mock.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.cli import main


def test_ask_creates_thread_and_returns_success(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    exit_code = main(["ask", "--prompt", "hello", "--workspace", "/tmp/project"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_ask_flow_mock.py -q`
Expected: FAIL because main ask flow is not implemented.

- [ ] **Step 3: Write minimal implementation**

Implement `ask` orchestration:

- infer thread key
- acquire lock
- load thread state if present
- choose new vs resume
- call Claude adapter
- update thread state
- write run record
- print answer text

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_ask_flow_mock.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/cli.py bridge/codex2claude/state.py bridge/codex2claude/claude_cli.py tests/test_ask_flow_mock.py
git commit -m "feat: implement codex2claude ask flow"
```

### Task 8: Implement Status, Forget, And Gc Commands

**Files:**
- Modify: `bridge/codex2claude/cli.py`
- Create: `tests/test_admin_commands.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.cli import main


def test_status_command_on_missing_thread_returns_nonzero(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    exit_code = main(["status", "--workspace", "/tmp/project"])
    assert exit_code != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_admin_commands.py -q`
Expected: FAIL because admin commands are not implemented.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `status`
- `forget`
- `gc`

Make output deterministic and script-friendly.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_admin_commands.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/cli.py tests/test_admin_commands.py
git commit -m "feat: add bridge admin commands"
```

### Task 9: Add Error Mapping And Logging

**Files:**
- Modify: `bridge/codex2claude/errors.py`
- Modify: `bridge/codex2claude/cli.py`
- Create: `bridge/codex2claude/logging_utils.py`
- Create: `tests/test_errors_and_logging.py`

- [ ] **Step 1: Write the failing test**

```python
from codex2claude.errors import EXIT_TIMEOUT


def test_timeout_exit_code_is_stable() -> None:
    assert EXIT_TIMEOUT == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_errors_and_logging.py -q`
Expected: FAIL because exit code constants and logger setup do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- stable exit code constants
- human-readable stderr formatting
- structured append-only bridge log
- per-run compact JSON artifact writing

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_errors_and_logging.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bridge/codex2claude/errors.py bridge/codex2claude/logging_utils.py bridge/codex2claude/cli.py tests/test_errors_and_logging.py
git commit -m "feat: add bridge error mapping and logging"
```

### Task 10: Add Real CLI Smoke Tests

**Files:**
- Create: `tests/test_real_claude_cli.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import shutil
import pytest


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI missing")
def test_real_claude_roundtrip_smoke() -> None:
    assert os.environ.get("PYTHONPATH") is not None or True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_real_claude_cli.py -q`
Expected: FAIL or remain skeletal because real smoke test logic is not implemented.

- [ ] **Step 3: Write minimal implementation**

Add opt-in real integration tests guarded by environment variable, covering:

- new ask
- resume ask
- `--new`

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m pytest tests/test_real_claude_cli.py -q`
Expected: PASS on configured machines.

- [ ] **Step 5: Commit**

```bash
git add tests/test_real_claude_cli.py
git commit -m "test: add opt-in real Claude CLI smoke coverage"
```

### Task 11: Add The Codex Skill Wrapper

**Files:**
- Create: `skills/codex-to-claude/SKILL.md`
- Create: `tests/test_skill_docs.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_skill_file_exists() -> None:
    assert Path("skills/codex-to-claude/SKILL.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_skill_docs.py -q`
Expected: FAIL because the skill file does not exist.

- [ ] **Step 3: Write minimal implementation**

Write `SKILL.md` that:

- declares when to use the skill
- instructs Codex to call `codex2claude ask`
- supports `--thread`, `--new`, `status`, `forget`, `gc`
- explicitly keeps Claude session/state logic out of the skill

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_skill_docs.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/codex-to-claude/SKILL.md tests/test_skill_docs.py
git commit -m "feat: add codex-to-claude Codex skill wrapper"
```

### Task 12: Add Packaging And Install Documentation

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `tests/test_package_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_pyproject_exists() -> None:
    assert Path("pyproject.toml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_package_metadata.py -q`
Expected: FAIL because packaging files do not exist.

- [ ] **Step 3: Write minimal implementation**

Create packaging metadata with a console script entry point for `codex2claude`, and document:

- installation
- bridge usage
- skill usage
- troubleshooting
- real test invocation

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_package_metadata.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md tests/test_package_metadata.py
git commit -m "docs: add packaging and bridge usage docs"
```

### Task 13: Add Concurrency And Recovery Tests

**Files:**
- Create: `tests/test_concurrency.py`

- [ ] **Step 1: Write the failing test**

```python
def test_placeholder_for_same_thread_lock_contention() -> None:
    assert False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_concurrency.py -q`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Replace placeholder with tests for:

- same-thread lock contention
- different-thread parallel success
- interrupted run leaves state readable

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=bridge python3 -m pytest tests/test_concurrency.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_concurrency.py
git commit -m "test: add bridge concurrency and recovery coverage"
```

### Task 14: Run Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run unit and mocked integration tests**

Run: `PYTHONPATH=bridge python3 -m pytest tests -q`
Expected: PASS except opt-in real CLI tests when disabled.

- [ ] **Step 2: Run real Claude CLI smoke tests**

Run: `PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m pytest tests/test_real_claude_cli.py -q`
Expected: PASS on configured machine.

- [ ] **Step 3: Dogfood the bridge manually**

Run:

```bash
PYTHONPATH=bridge python3 -m codex2claude ask --prompt "Reply with ok only" --workspace "$PWD"
PYTHONPATH=bridge python3 -m codex2claude ask --prompt "Now say resume-ok only" --workspace "$PWD"
PYTHONPATH=bridge python3 -m codex2claude status --workspace "$PWD"
```

Expected:

- first command succeeds
- second command resumes same thread successfully
- status shows persisted thread metadata

- [ ] **Step 4: Update docs with verified commands if needed**

Adjust `README.md` to match reality from verification.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "chore: verify codex2claude bridge end to end"
```
