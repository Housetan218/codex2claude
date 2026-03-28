---
name: codex-to-claude
description: Use when the user wants Codex to ask local Claude for a review, second opinion, or follow-up, including prompts like ask Claude, send to Claude, ask cc, cc review, 问问 cc, cc 怎么看, 给 Claude 看看, 给 cc 看看, 让 Claude 看一下, 让 cc 看一下, continue the Claude thread, or start a fresh Claude conversation.
---

# Codex To Claude

This skill is a thin wrapper around the local `codex2claude` bridge.

## Use Cases

- "ask Claude about this"
- "send this to Claude"
- "give this to Claude"
- "review this with Claude"
- "Claude second opinion"
- "cc review this"
- "ask cc about this"
- "ask cc"
- "send this to cc"
- "give this to cc"
- "cc怎么看"
- "cc觉得呢"
- "cc能帮忙看下吗"
- "问问cc"
- "问问 cc"
- "问下Claude"
- "问下 Claude"
- "Claude怎么看"
- "Claude 能看下吗"
- "让cc帮忙看看"
- "cc review下"
- "cc check一下"
- "let cc review this"
- "给 Claude 看看"
- "给 Claude review 一下"
- "让 Claude 看一下"
- "发给 Claude"
- "给 cc 看看"
- "给 cc review 一下"
- "让 cc 看一下"
- "发给 cc"
- "cc 怎么看"
- "cc 觉得呢"
- "cc 能帮忙看下吗"
- "让 cc 帮忙看看"
- "cc review 下"
- "cc check 一下"
- "Claude 怎么看"
- "Claude 能看下吗"
- "continue the Claude thread"
- "start a fresh Claude conversation for this workspace"

Treat `cc` as `Claude` when the request clearly means a Claude handoff or review.
Do not treat bare `cc` alone as a trigger unless the surrounding request clearly includes ask, review, check, or look intent.

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
