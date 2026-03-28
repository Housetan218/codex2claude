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

Common trigger phrases that should explicitly steer Codex toward this skill:

- `Use the codex-to-claude skill`
- `ask Claude about this`
- `send this to Claude`
- `let Claude review this`
- `ask cc`
- `ask cc about this`
- `cc review this`
- `cc 怎么看`
- `cc 觉得呢`
- `cc 能帮忙看下吗`
- `问问cc`
- `问下Claude`
- `Claude 怎么看`
- `Claude 能看下吗`
- `让cc帮忙看看`
- `cc review下`
- `cc check一下`
- `give this to cc`
- `给 Claude 看看`
- `让 Claude 看一下`
- `发给 Claude`
- `给 cc 看看`
- `让 cc review 一下`
- `发给 cc`

For stability, prefer phrases where `cc` appears with an action like ask, review, check, or look. Avoid relying on bare `cc` by itself.

## Triggering

Recommended everyday trigger phrases:

- `给cc看看这个`
- `问问cc`
- `cc怎么看`
- `让cc review一下`
- `给Claude看看`

More explicit variants:

- `Use the codex-to-claude skill`
- `ask Claude about this`
- `ask cc`
- `cc review this`
- `给 cc 看看`
- `问下Claude`

## Activation Scope

These paths are confirmed to work:

- new Codex sessions started after the skill was installed
- `codex exec` runs started after the skill was installed
- direct `codex2claude` CLI usage

Do not assume already-open Codex sessions will hot-reload newly installed or updated skills.

If you changed trigger phrases or installed the skill during an existing session, restart Codex or open a fresh session before testing.

## Troubleshooting

If a trigger phrase does not route to Claude:

1. Start a new Codex session.
2. Test with a high-signal phrase such as `问问cc：请只回复 ok`.
3. If needed, use the most explicit form: `Use the codex-to-claude skill. Ask Claude: ...`
4. Verify the bridge directly with `codex2claude ask --prompt "Reply with ok only" --workspace "$PWD"`.

If direct CLI usage works but a natural-language trigger does not, the issue is skill discovery in that session, not the bridge itself.

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
