import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


FAKE_CLAUDE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys

    args = sys.argv[1:]
    prompt = args[args.index("-p") + 1]
    payload = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": f"echo:{prompt}",
        "session_id": "recovered-session",
    }
    sys.stdout.write(json.dumps(payload))
    """
)


class RecoveryTest(unittest.TestCase):
    def test_corrupted_thread_state_is_replaced_on_next_ask(self) -> None:
        from codex2claude.cli import main
        from codex2claude.threading import make_thread_key

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(FAKE_CLAUDE, encoding="utf-8")
            fake_claude.chmod(0o755)

            thread_key = make_thread_key(str(workspace), None)
            thread_path = state_root / "threads" / f"{thread_key}.json"
            thread_path.parent.mkdir(parents=True, exist_ok=True)
            thread_path.write_text("{not-json", encoding="utf-8")

            env = {
                "CODEX2CLAUDE_HOME": str(state_root),
                "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"):
                exit_code = main(["ask", "--prompt", "hello", "--workspace", str(workspace)])

            repaired = json.loads(thread_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(repaired["claude_session_id"], "recovered-session")


if __name__ == "__main__":
    unittest.main()
