# Codex-to-Claude v1 Design

**Date:** 2026-03-28

## Implementation Status

Implemented in this repo:

- bridge package under `bridge/codex2claude/`
- thin Codex skill wrapper under `skills/codex-to-claude/`
- unit and mocked integration coverage under `tests/`
- opt-in real Claude smoke coverage under `tests/test_real_claude_cli.py`

Fresh local verification performed after implementation:

- full unittest suite
- real Claude new-session smoke
- real Claude resume smoke

## Goal

Build a production-quality local `Codex -> Claude` bridge for one-way communication:

- Users invoke a Codex-facing skill.
- The skill calls a local reusable bridge executable.
- The bridge owns all Claude CLI interaction, session persistence, locking, logging, timeout handling, and error translation.

This v1 is intentionally one-way only. Bidirectional agent-to-agent protocols are out of scope.

## Final Architecture

### User Entry

The primary entrypoint is a Codex skill named `codex-to-claude`.

The skill is intentionally thin:

- Accept user prompt and a small set of bridge-level flags.
- Resolve current workspace root.
- Invoke the local bridge executable.
- Return bridge stdout as the Claude answer.
- Return bridge stderr and exit status as actionable user-facing failures.

### Bridge

The bridge is a local Python 3 CLI named `codex2claude`.

It is the system boundary between Codex and Claude. All Claude-specific complexity lives here:

- Start a Claude conversation.
- Resume a Claude conversation with stored `session_id`.
- Persist per-thread state.
- Enforce single-writer access per thread.
- Enforce timeout and process cleanup.
- Parse Claude JSON output.
- Normalize errors into stable exit codes.
- Record debug and run logs.

### Why Python 3

Python 3 is the correct implementation language for this machine and this version:

- Available locally.
- macOS-compatible file locking via `fcntl`.
- Native JSON parsing.
- Native subprocess timeout support.
- No external runtime dependencies required.

Bash was rejected because the local machine does not provide `flock`, `jq`, or `timeout`, which would make a Bash bridge operationally fragile.

## Session Model

### Core Decision

The bridge will persist Claude `session_id` and use native `claude --resume <session-id>` for follow-up turns.

It will not persist or replay full message history in v1.

### Why

- Claude CLI already owns conversation persistence.
- This removes custom replay logic and context reconstruction risk.
- It minimizes local state surface area.
- It uses the Claude CLI capability already verified on this machine.

## Thread Model

The bridge stores state by local thread key, not by opaque Codex internals.

### Default Thread Key

Default thread key is derived from:

- canonical workspace root
- bridge mode identifier (`codex-to-claude`)

This gives one default Claude thread per workspace unless the user requests a named thread.

### Named Threads

Users may optionally provide `--thread <name>` to isolate separate Claude conversations inside the same workspace.

### Force New

Users may pass `--new` to ignore any stored `session_id` and start a fresh Claude conversation for the current thread key.

## Bridge CLI Contract

### Commands

`codex2claude ask`

- Main command.
- Starts or resumes a Claude conversation for a thread.

`codex2claude status`

- Prints stored thread metadata and health.

`codex2claude forget`

- Deletes stored thread state for the selected thread.

`codex2claude gc`

- Removes stale thread files and old run logs according to retention policy.
- Current implementation removes stale thread files. Run-log retention can be extended later without changing the user-facing command.

### Main Command Shape

```bash
codex2claude ask --prompt "..." [--thread design] [--new] [--timeout 300] [--workspace /abs/path]
```

### Input Contract

- Prompt is passed as an explicit CLI argument, not raw stdin.
- Workspace root is explicit or inferred from current working directory.
- Thread name is optional.

### Output Contract

Stdout:

- Claude textual answer only.

Stderr:

- Structured human-readable operational messages.
- Never mix Claude answer text into stderr.

Exit codes:

- `0` success
- `1` Claude invocation failure
- `2` timeout
- `3` thread lock conflict
- `4` invalid arguments or config
- `5` corrupted state or persistence failure

## Claude Invocation Contract

### New Conversation

```bash
claude -p "<prompt>" --output-format json
```

### Resume Conversation

```bash
claude --resume "<session_id>" -p "<prompt>" --output-format json
```

### Parsing

The bridge parses the Claude JSON envelope with Python `json`.

The bridge extracts at minimum:

- `session_id`
- `result`
- `is_error` if present
- raw envelope for logging

If Claude returns malformed or unexpected JSON:

- the bridge records the raw payload
- returns a parse failure
- does not silently treat malformed output as success

## State Storage

### Root Directory

```text
~/.codex/codex2claude/
```

### Layout

```text
~/.codex/codex2claude/
  threads/
    <thread_key>.json
  runs/
    <thread_key>/
      <timestamp>.json
  logs/
    bridge.log
```

### Persisted Per Thread

- `thread_key`
- `workspace_root`
- `thread_name`
- `claude_session_id`
- `created_at`
- `last_used_at`
- `last_status`
- `bridge_version`
- `claude_version`
- `last_error`

### Persisted Per Run

- `run_id`
- `thread_key`
- `started_at`
- `ended_at`
- `duration_ms`
- `used_resume`
- `prompt_sha256`
- `exit_code`
- `parse_ok`
- `stdout_preview`
- `stderr_preview`

The bridge should avoid persisting full prompt text by default. Hashes and previews are sufficient for operational tracing.

## Locking and Concurrency

### Locking

Use Python `fcntl.flock()` on the thread state file or a dedicated lock file.

### Policy

- One active `ask` per thread.
- Concurrent calls on different threads are allowed.
- Concurrent calls on the same thread fail fast with exit code `3`.

This avoids queueing complexity in v1 and keeps behavior deterministic.

## Timeout and Cancellation

The bridge uses Python subprocess timeout handling.

### Default

- 300 seconds

### Behavior

- On timeout, terminate Claude subprocess.
- If graceful termination fails, kill the process.
- Record timeout in thread state and run log.
- Return exit code `2`.

## Logging

### Operational Log

Append structured records to:

```text
~/.codex/codex2claude/logs/bridge.log
```

Each log event should include:

- timestamp
- level
- thread_key
- run_id
- action
- outcome

### Run Artifacts

Each invocation writes a compact JSON record under `runs/`.

This is the primary debugging surface for post-failure diagnosis.

## Error Handling

The bridge is responsible for turning Claude/process/state failures into deterministic user-facing outcomes.

### Required Cases

- Claude CLI missing
- Claude invocation non-zero exit
- timeout
- malformed JSON
- stale or invalid `session_id`
- corrupted thread file
- lock contention
- write failure on state persistence

### Session Expiration Handling

If `--resume` fails because the Claude session is no longer valid:

- record the failure
- start a fresh conversation automatically only when safe and unambiguous
- otherwise surface a clear error instructing the user to rerun with `--new`

For v1, deterministic behavior is preferred over clever implicit recovery. If the reason is ambiguous, fail clearly.

## Codex Skill Contract

### The Skill Must Do

- Collect user prompt.
- Accept small bridge-facing flags such as `--thread` and `--new`.
- Invoke `codex2claude ask`.
- Print Claude response.
- Surface bridge failures cleanly.

### The Skill Must Not Do

- Parse Claude JSON.
- Store Claude session IDs.
- Implement retries.
- Reconstruct history.
- Embed Claude CLI contract details.

## Testing Strategy

### Unit Tests

- thread key generation
- state file read/write
- lock acquisition/release
- exit code mapping
- Claude envelope parsing
- timeout handling

### Mocked Integration Tests

Use a fake `claude` executable to cover:

- successful new session
- successful resume
- malformed JSON
- timeout
- non-zero exit
- invalid session on resume

### Real Claude CLI Tests

- first ask
- second ask resumes same thread
- named thread isolation
- `--new` starts fresh session
- `forget` resets thread state

### Concurrency Tests

- same-thread contention
- different-thread parallel success
- interrupted run does not corrupt stored thread state

### Manual Dogfooding

Require repeated real Codex-to-Claude use before calling v1 stable.

## Stability Bar For v1

Do not call this stable until:

- unit tests pass
- mocked integration tests pass
- real Claude CLI tests pass
- same-thread concurrency is deterministic
- repeated real usage shows no thread corruption
- operational logs are sufficient to diagnose failures

## Out of Scope

- bidirectional Codex/Claude protocol
- streaming Claude output
- automatic queueing of concurrent same-thread requests
- message-history replay
- remote bridge server
- MCP-based Claude transport

## Future Extension Path

The bridge should be designed so later versions can add:

- dual-review mode
- explicit multi-agent protocol
- richer per-thread metadata
- optional streaming mode
- optional MCP transport

The skill entrypoint should remain stable when those extensions arrive.
