# Contributing

Thanks for contributing to `codex2claude`.

## Development Setup

Create a virtual environment and install the project in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

If you need packaging checks locally:

```bash
python3 -m pip install build twine
```

## Running Tests

Run the full unit test suite:

```bash
PYTHONPATH=bridge python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Run the opt-in real Claude smoke tests:

```bash
PYTHONPATH=bridge CODEX2CLAUDE_RUN_REAL=1 python3 -m unittest tests.test_real_claude_cli -v
```

The real-Claude tests require local Claude auth and spend actual Claude usage.

## Manual Verification

Direct CLI smoke:

```bash
codex2claude ask --prompt "Reply with ok only" --workspace "$PWD" --new
```

Diagnostic smoke:

```bash
codex2claude doctor --workspace "$PWD"
```

Natural-language skill smoke in a fresh Codex session:

```bash
codex exec -C "$PWD" --dangerously-bypass-approvals-and-sandbox "问问cc：请只回复 ok，不要输出别的内容。"
```

## Skill Changes

If you change [SKILL.md](./skills/codex-to-claude/SKILL.md):

- keep the skill thin
- do not move session logic out of the bridge
- verify at least one natural-language trigger in a fresh Codex session
- document any new trigger phrases in [README.md](./README.md)

## Release Checklist

Before tagging a release:

1. Run the full unit test suite.
2. Run a real `codex2claude ask` smoke test.
3. Run a real natural-language Codex skill trigger smoke test in a fresh session.
4. Build the distribution artifacts.
5. Run `twine check dist/*`.
6. Update README and release notes if trigger behavior changed.

Build artifacts:

```bash
python3 -m build
python3 -m twine check dist/*
```

## GitHub Actions

This repository ships with:

- `.github/workflows/test.yml`: runs unit tests and packaging checks on push and pull request
- `.github/workflows/release.yml`: builds distributions and publishes to PyPI on version tags

## PyPI Trusted Publishing

The release workflow is configured for PyPI Trusted Publishing, which is the current recommended approach for GitHub Actions based publishing.

PyPI project configuration should trust:

- owner: `Housetan218`
- repository: `codex2claude`
- workflow: `.github/workflows/release.yml`
- environment: `pypi`

If `codex2claude` does not yet exist on PyPI, create it with PyPI's Trusted Publishing flow for a new project and register the same repository, workflow, and environment there first.

After that is configured on PyPI, pushing a tag like `v0.1.2` will build and publish the package without a manually managed API token.

## Pull Requests

- Keep changes focused.
- Include tests or a clear reason why tests are not needed.
- Call out any changes to trigger phrases, session behavior, or release steps.
