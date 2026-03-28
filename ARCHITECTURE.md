# Architecture

## Overview

`codex2claude` is intentionally small. The architecture has three layers:

1. CLI commands that define user-visible behavior
2. bridge internals that invoke Claude, manage thread identity, and persist state
3. a thin Codex skill that converts natural-language intent into CLI calls

The bridge is local-only and depends on the local Claude CLI as the execution backend.

## Main Flow

The normal `ask` flow is:

1. resolve the canonical workspace root
2. derive a deterministic thread key from workspace root and optional thread name
3. acquire a non-blocking per-thread file lock
4. load existing thread state unless `--new` was requested
5. call the local `claude` CLI with either a fresh prompt or `--resume <session_id>`
6. parse Claude's JSON response
7. persist updated thread state and a run artifact
8. append a structured bridge log entry
9. render either prefixed text output or structured JSON to stdout

## Command Responsibilities

### `ask`

- owns the end-to-end request flow
- persists the latest Claude `session_id`
- emits run records for observability
- returns either `[model: <name>] <reply>` or JSON via `--json`
- resolves the model name from Claude JSON without adding extra bridge-side session logic

### `status`

- reads and prints the current thread-state JSON for the selected workspace/thread

### `forget`

- deletes the saved thread-state file and lock file for the selected workspace/thread

### `gc`

- removes stale thread files, lock files, and run directories
- skips active thread keys that are currently locked

### `doctor`

- diagnoses bridge path layout
- checks whether `claude --version` is readable
- reports whether the selected thread state is `ok`, `missing`, or `error`

## Thread Identity Model

Thread identity is derived by:

- canonicalizing `--workspace` with `Path(...).expanduser().resolve()`
- combining canonical workspace root with optional thread name
- hashing that tuple into a stable SHA-256 thread key

This gives stable thread reuse across repeated invocations in the same repo while still allowing named subthreads.

## Persistence Model

State root:

```text
~/.codex/codex2claude/
  threads/
  runs/
  logs/
```

Key files:

- `threads/<thread_key>.json`: current thread state
- `threads/<thread_key>.lock`: lock file used for same-thread exclusion
- `runs/<thread_key>/*.json`: per-run artifacts
- `logs/bridge.log`: append-only JSONL log

Thread state fields currently include:

- workspace identity
- optional thread name
- Claude `session_id`
- creation and last-used timestamps
- last status
- bridge version
- Claude version
- last error

Run artifacts currently include:

- run id
- timing
- whether resume was used
- prompt hash
- exit code
- parse status
- stdout/stderr previews

Writes use temp files plus replace semantics to avoid partial-state corruption.

Example thread-state document:

```json
{
  "thread_key": "<sha256>",
  "workspace_root": "/path/to/repo",
  "thread_name": "docs",
  "claude_session_id": "<claude-session-id>",
  "created_at": "2026-03-28T00:00:00Z",
  "last_used_at": "2026-03-28T03:25:11Z",
  "last_status": "ok",
  "bridge_version": "0.1.3",
  "claude_version": "2.x.x (Claude Code)",
  "last_error": null
}
```

Example run-record document:

```json
{
  "run_id": "<uuid>",
  "thread_key": "<sha256>",
  "started_at": "2026-03-28T03:25:10Z",
  "ended_at": "2026-03-28T03:25:11Z",
  "duration_ms": 842,
  "used_resume": true,
  "prompt_sha256": "<sha256>",
  "exit_code": 0,
  "parse_ok": true,
  "stdout_preview": "Claude reply preview",
  "stderr_preview": ""
}
```

## Claude CLI Adapter

`bridge/codex2claude/claude_cli.py` is the only module that should know how to:

- build the `claude` command line
- invoke the subprocess
- interpret timeout and missing-binary failures
- parse Claude JSON output

Expected Claude contract:

- output format is JSON
- `result` is the human-readable reply
- `session_id` may be returned and later reused with `--resume`
- `modelUsage` may expose one or more concrete model identifiers for the response

Current model-resolution policy:

- prefer the first string key in `modelUsage`
- fall back to `model` or `model_name` when present
- render `unknown` when the Claude payload does not expose a model identifier

If Claude returns malformed JSON or invalid fields, the bridge treats that as state/contract corruption rather than silently guessing.

## Concurrency Model

Concurrency protection is intentionally narrow:

- locking is per thread key, not global
- different threads can run independently
- the same thread key cannot be updated concurrently

Locking uses `fcntl.flock(...)`, so the current implementation targets macOS/POSIX rather than Windows.

## Error Model

Exit codes are centralized in `bridge/codex2claude/errors.py`.

Important categories:

- generic Claude invocation failures
- Claude timeout
- lock conflict
- invalid arguments
- state corruption

Current mapping:

- `BridgeError` -> `1`
- `ClaudeInvocationError` -> `1`
- `ClaudeTimeoutError` -> `2`
- `LockConflictError` -> `3`
- `InvalidArgumentsError` -> `4`
- `StateCorruptionError` -> `5`

The CLI catches `BridgeError` subclasses, logs them, prints a short stderr message, and exits with the mapped code.

## Skill Layer

`skills/codex-to-claude/SKILL.md` is intentionally not part of the bridge core.

Its job is only to:

- identify user intent like "问问cc" or "给 Claude 看看"
- choose default thread, named thread, or fresh thread mode
- call `codex2claude ask`
- surface stdout/stderr

The skill should not own:

- Claude JSON parsing
- state-file mutation
- retries
- custom session bookkeeping

## Design Constraints

- prefer simple stdlib-based implementation inside the bridge
- keep user-visible behavior deterministic
- favor explicit recovery over hidden repair
- document every user-facing command and every release step

## Near-Term Evolution

The current roadmap is in `docs/roadmaps/2026-03-28-v0.2.0-roadmap.md`.

Planned evolution is incremental:

- improve diagnostics and troubleshooting
- improve release safety and version consistency
- improve usage docs and trigger verification

Bidirectional multi-agent coordination remains intentionally out of scope until the one-way bridge stays stable under real use.
