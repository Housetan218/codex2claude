# codex2claude

`codex2claude` is a local one-way bridge from Codex to Claude.

It provides:

- a reusable Python CLI bridge
- Claude session persistence via native `session_id`
- deterministic per-thread locking
- a thin Codex skill wrapper surface
- no non-stdlib Python runtime dependency inside the bridge

Current implementation target:

- macOS / POSIX environments with Python 3 and local Claude CLI access
- not designed for Windows in its current `fcntl`-based form

## Current Status

Implemented and locally verified on this machine:

- `ask`
- `status`
- `forget`
- `gc`
- automatic resume via stored Claude `session_id`
- same-thread lock conflict handling

Fresh verification completed during implementation:

- `PYTHONPATH=bridge python3 -m unittest discover -s tests -p 'test_*.py' -v`
- real Claude new-session smoke
- real Claude resume smoke

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

If you do not want to install it yet, you can run it directly:

```bash
PYTHONPATH=bridge python3 -m codex2claude ask --prompt "Reply with ok only"
```

After editable install, both of these work:

```bash
python -m codex2claude --help
codex2claude --help
```

## Usage

Ask Claude in the current workspace thread:

```bash
codex2claude ask --prompt "Review this design" --workspace "$PWD"
```

Use a named thread:

```bash
codex2claude ask --prompt "Continue the design review" --workspace "$PWD" --thread design
```

Force a fresh Claude session:

```bash
codex2claude ask --prompt "Start over" --workspace "$PWD" --new
```

Inspect stored state:

```bash
codex2claude status --workspace "$PWD"
```

Forget the current thread:

```bash
codex2claude forget --workspace "$PWD"
```

Remove stale thread files:

```bash
codex2claude gc --max-age-days 7
```

## Codex Skill

The Codex-facing wrapper lives at:

```text
skills/codex-to-claude/SKILL.md
```

The skill should stay thin. It should only:

- collect the user prompt
- choose default thread, named thread, or `--new`
- invoke `codex2claude`
- return stdout or surface stderr

It should not own Claude JSON parsing, session files, or retries.

## Threading Model

By default, one workspace maps to one Claude thread.

Use `--thread <name>` to split conversations inside the same repo:

```bash
codex2claude ask --prompt "Review API design" --workspace "$PWD" --thread api
codex2claude ask --prompt "Review docs tone" --workspace "$PWD" --thread docs
```

Use `--new` when you want a fresh Claude conversation for the selected thread key.

## Environment

- `CODEX2CLAUDE_CLAUDE_BIN`: override the Claude executable path
- `CODEX2CLAUDE_HOME`: override the bridge state root without changing your real shell `HOME`
- `CODEX2CLAUDE_RUN_REAL=1`: enable opt-in real Claude integration tests

## Test

Run the main test suite:

```bash
PYTHONPATH=bridge python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run the opt-in real Claude smoke test:

```bash
PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m unittest tests.test_real_claude_cli -v
```

The real-Claude test is opt-in because it spends actual Claude usage and requires local auth.

## Exit Codes

- `0`: success
- `1`: Claude invocation failure or generic bridge failure
- `2`: Claude timeout
- `3`: same-thread lock conflict
- `4`: invalid arguments
- `5`: corrupted state or persistence failure

## State Layout

```text
~/.codex/codex2claude/
  threads/
  runs/
  logs/
```

Important files:

- `threads/<thread_key>.json`: current thread state and stored Claude `session_id`
- `runs/<thread_key>/...json`: per-run artifacts
- `logs/bridge.log`: append-only bridge events

## Current Scope

This version is intentionally one-way only:

- Codex initiates
- Claude replies
- bridge stores Claude `session_id`
- follow-up turns use native `claude --resume`

Bidirectional agent protocols are out of scope for v1.

## References

- Design: `docs/superpowers/specs/2026-03-28-codex-to-claude-design.md`
- Plan: `docs/superpowers/plans/2026-03-28-codex-to-claude-v1.md`
