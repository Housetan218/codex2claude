# AGENTS.md

This file is for coding agents and developers working in this repository.

## Project Summary

`codex2claude` is a local one-way bridge from Codex to Claude.

Current scope:

- Codex sends a prompt to Claude through the local `claude` CLI
- the bridge stores Claude `session_id`
- later asks can resume the same Claude thread
- `ask` surfaces the resolved Claude model in its output
- a thin Codex skill maps natural-language requests onto the bridge CLI

Out of scope for the current product:

- bidirectional Codex-Claude protocols
- bridge-owned retry orchestration
- non-local or hosted service dependencies

## Repository Map

- `bridge/codex2claude/cli.py`: CLI entrypoints for `ask`, `status`, `forget`, `gc`, `doctor`
- `bridge/codex2claude/claude_cli.py`: Claude subprocess invocation and JSON parsing
- `bridge/codex2claude/state.py`: thread-state and run-record persistence
- `bridge/codex2claude/threading.py`: canonical workspace resolution and thread-key hashing
- `bridge/codex2claude/locking.py`: per-thread file lock
- `bridge/codex2claude/paths.py`: state-root path layout
- `skills/codex-to-claude/SKILL.md`: Codex-facing trigger surface
- `tests/`: unit tests and opt-in real Claude smoke tests
- `README.md`: user-facing usage docs
- `DEVELOPMENT.md`: developer workflow and verification handbook
- `CONTRIBUTING.md`: development and release workflow
- `ARCHITECTURE.md`: design and data-flow reference

## Core Invariants

- Keep the skill thin. Session logic belongs in the bridge, not in `SKILL.md`.
- One workspace plus optional thread name maps to one deterministic thread key.
- Resume behavior must use Claude's native `session_id`.
- State writes should remain atomic via temp-file replace.
- Same-thread concurrent asks must fail with lock conflict, not corrupt state.
- `doctor` should stay focused on bridge health, Claude availability, and thread-state diagnostics.
- Human-readable `ask` output should keep model visibility without moving session logic into the skill.

## Common Commands

Editable install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Run tests:

```bash
PYTHONPATH=bridge python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run real Claude smoke tests:

```bash
PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m unittest tests.test_real_claude_cli -v
```

Bridge smoke:

```bash
codex2claude ask --prompt "Reply with ok only" --workspace "$PWD" --new
codex2claude ask --prompt "Reply with ok only" --workspace "$PWD" --new --json
codex2claude doctor --workspace "$PWD"
```

Skill smoke in a fresh Codex session:

```bash
codex exec -C "$PWD" --dangerously-bypass-approvals-and-sandbox "问问cc：请只回复 ok，不要输出别的内容。"
```

Packaging:

```bash
python3 -m venv .venv-release
. .venv-release/bin/activate
python3 -m pip install build twine
.venv-release/bin/python -m build
.venv-release/bin/python -m twine check dist/*
```

## Change Guidance

When changing CLI behavior:

- update unit tests first or in the same change
- keep exit codes aligned with `bridge/codex2claude/errors.py`
- update `README.md` if user-visible behavior changes

When changing state shape:

- preserve compatibility when practical
- update `doctor` output expectations and related tests
- document the new fields and failure modes

When changing skill triggers:

- update `skills/codex-to-claude/SKILL.md`
- update trigger examples in `README.md`
- verify at least one natural-language trigger in a fresh Codex session

## Release Notes For Agents

- GitHub release publishing is tag-driven through `.github/workflows/release.yml`
- PyPI publishing uses Trusted Publishing for the main repository
- do not claim a release succeeded until GitHub Actions and PyPI both confirm it

## Preferred Next Work

See `docs/roadmaps/2026-03-28-v0.2.0-roadmap.md` before starting post-`v0.1.3` feature work.
