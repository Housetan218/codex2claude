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
- `doctor`
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

When a PyPI release is available, install with:

```bash
python3 -m pip install codex2claude
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

Ask Claude and get structured output:

```bash
codex2claude ask --prompt "Review this design" --workspace "$PWD" --json
```

Inspect stored state:

```bash
codex2claude status --workspace "$PWD"
```

Run diagnostics:

```bash
codex2claude doctor --workspace "$PWD"
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
5. Run `codex2claude doctor --workspace "$PWD"` to confirm the Claude CLI and thread-state diagnostics.

If direct CLI usage works but a natural-language trigger does not, the issue is skill discovery in that session, not the bridge itself.

## Threading Model

By default, one workspace maps to one Claude thread.

Use `--thread <name>` to split conversations inside the same repo:

```bash
codex2claude ask --prompt "Review API design" --workspace "$PWD" --thread api
codex2claude ask --prompt "Review docs tone" --workspace "$PWD" --thread docs
```

Use `--new` when you want a fresh Claude conversation for the selected thread key.

By default, `ask` now prefixes the visible reply with the resolved Claude model name:

```text
[model: claude-opus-4-6[1m]] <reply text>
```

Use `--json` when you need structured output instead of the prefixed text form. The JSON shape is:

```json
{
  "model": "claude-opus-4-6[1m]",
  "reply": "hello",
  "session_id": "7f094c44-8dff-49dc-8830-70afe1135955"
}
```

`session_id` may be `null` if Claude does not return a reusable session for that response.

Model resolution rules:

- prefer the first model key found in Claude's `modelUsage`
- fall back to `model` or `model_name` if present
- use `unknown` if the Claude payload does not expose model information

## Environment

- `CODEX2CLAUDE_CLAUDE_BIN`: override the Claude executable path
- `CODEX2CLAUDE_HOME`: override the bridge state root without changing your real shell `HOME`
- `CODEX2CLAUDE_RUN_REAL=1`: enable opt-in real Claude integration tests

## Doctor Output

`codex2claude doctor --workspace "$PWD"` prints JSON and checks:

- the resolved bridge root and key paths
- whether the Claude CLI version can be read
- whether the selected thread state is present, missing, or corrupted

It returns `0` when required checks are healthy and non-zero when the Claude CLI check fails or thread state is corrupted.

Typical output shape:

```json
{
  "ok": true,
  "bridge_version": "0.1.3",
  "workspace_root": "/path/to/repo",
  "bridge_root": {
    "status": "ok",
    "path": "/Users/you/.codex/codex2claude"
  },
  "paths": {
    "threads": "/Users/you/.codex/codex2claude/threads",
    "logs": "/Users/you/.codex/codex2claude/logs",
    "state_file": "/Users/you/.codex/codex2claude/threads/<thread_key>.json"
  },
  "claude": {
    "status": "ok",
    "bin": "claude",
    "version": "2.x.x (Claude Code)"
  },
  "thread_state": {
    "status": "ok",
    "path": "/Users/you/.codex/codex2claude/threads/<thread_key>.json",
    "thread_key": "<sha256>",
    "session_id": "<claude-session-id>",
    "last_status": "ok",
    "last_used_at": "2026-03-28T03:25:11Z"
  }
}
```

Field meanings:

- `ok`: overall health for the selected workspace thread
- `bridge_version`: installed bridge version that produced the report
- `workspace_root`: canonical workspace path used for thread identity
- `bridge_root.path`: state root currently used by the bridge
- `paths.state_file`: exact thread-state file for this workspace and thread name
- `claude.status`: `ok` when `claude --version` can be read, otherwise `error`
- `thread_state.status`: `ok`, `missing`, or `error`

Interpretation guide:

- `claude.status = ok` and `thread_state.status = missing`: healthy first-use state
- `claude.status = ok` and `thread_state.status = ok`: healthy reusable thread state
- `claude.status = error`: Claude CLI is not reachable from this shell
- `thread_state.status = error`: the saved state file exists but could not be parsed or validated

Common fixes:

- Claude CLI unavailable:
  Run `claude --version` directly. If that fails, fix your Claude CLI install or shell `PATH`. If you use a custom binary, set `CODEX2CLAUDE_CLAUDE_BIN`.
- Unexpected bridge path:
  Check whether `CODEX2CLAUDE_HOME` is set. If it is unset, the default state root is `~/.codex/codex2claude`.
- Corrupted thread state:
  Run `codex2claude forget --workspace "$PWD"` and retry `ask`. This removes the saved state for the selected thread key and allows a clean new session.
- Wrong workspace identity:
  `workspace_root` is canonicalized before hashing. If you expected a different thread, verify the exact `--workspace` path and any `--thread <name>` value you used.

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

Error-class mapping:

- `BridgeError`: base error type, defaults to exit code `1`
- `ClaudeInvocationError`: Claude CLI not found, non-zero Claude exit, or generic Claude failure, exit code `1`
- `ClaudeTimeoutError`: Claude subprocess timeout, exit code `2`
- `LockConflictError`: same-thread lock conflict, exit code `3`
- `InvalidArgumentsError`: invalid CLI arguments or unsupported command path, exit code `4`
- `StateCorruptionError`: malformed Claude JSON, invalid state shape, or corrupted persisted state, exit code `5`

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

Typical thread-state shape:

```json
{
  "thread_key": "<sha256>",
  "workspace_root": "/path/to/repo",
  "thread_name": null,
  "claude_session_id": "<claude-session-id>",
  "created_at": "2026-03-28T00:00:00Z",
  "last_used_at": "2026-03-28T03:25:11Z",
  "last_status": "ok",
  "bridge_version": "0.1.3",
  "claude_version": "2.x.x (Claude Code)",
  "last_error": null
}
```

Typical run-record shape:

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

## Skill Debugging

When the natural-language trigger path is the problem, separate skill discovery from bridge behavior:

1. Verify the bridge first:
   `codex2claude ask --prompt "Reply with ok only" --workspace "$PWD" --new`
2. Start a fresh Codex session before testing trigger changes.
3. Use a high-signal trigger:
   `问问cc：请只回复 ok，不要输出别的内容。`
4. If that still fails, use the explicit form:
   `Use the codex-to-claude skill. Ask Claude: Reply with ok only.`
5. Check `skills/codex-to-claude/SKILL.md` for the exact trigger surface.

Important limitations:

- this repository does not provide a dedicated Codex skill-discovery log
- `logs/bridge.log` only records bridge activity after `codex2claude` is actually invoked
- if direct CLI usage works but the natural-language trigger does not, the failure is in session skill loading or skill routing, not in the bridge core
- after editing `SKILL.md`, validate in a fresh Codex session; do not assume hot reload in an already-open session

## FAQ

- Why does resume fail after it worked earlier?
  The saved Claude `session_id` may no longer be reusable, or the thread state may be corrupted. Run `codex2claude doctor --workspace "$PWD"`, then `codex2claude forget --workspace "$PWD"` if you need a clean thread.
- What should I do when I hit a lock conflict?
  Another process is already using the same workspace/thread key. Wait for the other run to finish, or use a different `--thread <name>` if you intentionally want a separate conversation.
- Can multiple workspaces share one Claude thread?
  Not by default. Thread identity includes the canonical workspace path, so different workspaces intentionally map to different thread keys unless you build a different policy.

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
- Roadmap: `docs/roadmaps/2026-03-28-v0.2.0-roadmap.md`
- Agent Guide: `AGENTS.md`
- Architecture: `ARCHITECTURE.md`
- Development Handbook: `DEVELOPMENT.md`

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development, verification, and release steps.

## CI And Releases

GitHub Actions runs unit tests and packaging checks on pushes and pull requests.

PyPI publishing is wired through `.github/workflows/release.yml` and currently uses PyPI Trusted Publishing from GitHub Actions for the main repository. If you fork this project, configure the matching trusted publisher entry on PyPI before expecting tag-based publishing to succeed in your fork.

For local packaging on Homebrew-managed Python, prefer a dedicated virtual environment for `build` and `twine` instead of installing them into the system interpreter.
