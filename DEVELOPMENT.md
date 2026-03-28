# Development

This document is the day-to-day developer handbook for `codex2claude`.

For repository goals and guardrails, see `AGENTS.md`.
For system design, see `ARCHITECTURE.md`.
For user-facing install and usage, see `README.md`.

## Local Setup

Editable development environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Packaging environment:

```bash
python3 -m venv .venv-release
. .venv-release/bin/activate
python3 -m pip install build twine
```

## Main Commands

Run the full unit test suite:

```bash
PYTHONPATH=bridge python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run the opt-in real Claude smoke tests:

```bash
PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m unittest tests.test_real_claude_cli -v
```

Bridge smoke:

```bash
codex2claude ask --prompt "Reply with ok only" --workspace "$PWD" --new
codex2claude doctor --workspace "$PWD"
```

Fresh-session skill smoke:

```bash
codex exec -C "$PWD" --dangerously-bypass-approvals-and-sandbox "问问cc：请只回复 ok，不要输出别的内容。"
```

Build distributions:

```bash
.venv-release/bin/python -m build
.venv-release/bin/python -m twine check dist/*
```

## Test Matrix

Use this as the minimum verification bar:

- bridge code change:
  run the full unit test suite
- CLI behavior change:
  run unit tests and at least one direct `codex2claude` smoke command
- skill trigger change:
  run unit tests and one fresh-session natural-language trigger smoke
- packaging or release change:
  run unit tests, build distributions, and `twine check`
- Claude integration change:
  run the opt-in real Claude smoke tests if local auth is available

## Development Workflow

1. Make the change in the smallest coherent slice.
2. Update tests in the same change when behavior shifts.
3. Update docs in the same change for any user-visible or developer-visible change.
4. Verify with the minimum test matrix above.
5. Review the diff before commit.

## Release Workflow

1. Confirm the working tree is clean.
2. Run the full unit test suite.
3. Run a real `codex2claude ask` smoke test.
4. Run a real fresh-session skill smoke test.
5. Build the distributions in `.venv-release`.
6. Run `.venv-release/bin/python -m twine check dist/*`.
7. Tag the release.
8. Push the tag.
9. Confirm GitHub Actions release workflow succeeds.
10. Confirm the version appears on PyPI.

## State And Debugging

Default state root:

```text
~/.codex/codex2claude/
```

Useful locations:

- `threads/`: stored thread state and lock files
- `runs/`: run artifacts per thread key
- `logs/bridge.log`: append-only JSONL bridge events

Useful debugging commands:

```bash
codex2claude status --workspace "$PWD"
codex2claude doctor --workspace "$PWD"
codex2claude forget --workspace "$PWD"
codex2claude gc --max-age-days 7
```

Skill debugging notes:

- there is no dedicated skill-discovery log in this repository
- `logs/bridge.log` is only useful after the skill has successfully invoked `codex2claude`
- if direct CLI commands work but a trigger phrase does not, test again in a fresh Codex session
- after changing `skills/codex-to-claude/SKILL.md`, validate with a fresh session rather than an already-open one

## Files You Usually Need

- `bridge/codex2claude/cli.py`
- `bridge/codex2claude/claude_cli.py`
- `bridge/codex2claude/state.py`
- `bridge/codex2claude/threading.py`
- `bridge/codex2claude/locking.py`
- `skills/codex-to-claude/SKILL.md`
- `tests/test_admin_commands.py`
- `tests/test_ask_flow_mock.py`
- `tests/test_real_claude_cli.py`

## Current Boundaries

- one-way Codex-to-Claude only
- local Claude CLI only
- POSIX locking only
- no hidden repair logic inside the bridge
