---
name: codex-to-claude
description: Use when the user wants Codex to send a prompt to local Claude and get Claude's answer back, with session continuity handled by a local bridge.
---

# Codex To Claude

This skill is a thin wrapper around the local `codex2claude` bridge.

## Use Cases

- "ask Claude about this"
- "send this to Claude"
- "continue the Claude thread"
- "start a fresh Claude conversation for this workspace"

## Rules

- Keep this skill thin.
- Do not parse Claude JSON in the skill.
- Do not manage Claude session files in the skill.
- Do not implement retries in the skill.
- Let `codex2claude` own session state, timeout handling, and error translation.

## Commands

Default ask in current workspace thread:

```bash
codex2claude ask --prompt "<USER_PROMPT>" --workspace "$PWD"
```

Named thread:

```bash
codex2claude ask --prompt "<USER_PROMPT>" --workspace "$PWD" --thread "<THREAD_NAME>"
```

Fresh thread:

```bash
codex2claude ask --prompt "<USER_PROMPT>" --workspace "$PWD" --new
```

Named fresh thread:

```bash
codex2claude ask --prompt "<USER_PROMPT>" --workspace "$PWD" --thread "<THREAD_NAME>" --new
```

Status:

```bash
codex2claude status --workspace "$PWD"
```

Forget:

```bash
codex2claude forget --workspace "$PWD"
```

Garbage collection:

```bash
codex2claude gc --max-age-days 7
```

## Behavior

1. Collect the user prompt.
2. Decide whether default thread, named thread, or `--new` is requested.
3. Invoke `codex2claude`.
4. Return stdout as Claude's answer.
5. If the bridge exits non-zero, surface stderr clearly.
6. Do not mutate bridge state outside the bridge itself.
