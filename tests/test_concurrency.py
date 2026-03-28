import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


SLOW_FAKE_CLAUDE = """#!/usr/bin/env python3
import json
import sys
import time

time.sleep(0.4)
sys.stdout.write(json.dumps({
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "done",
    "session_id": "slow-session"
}))
"""


class ConcurrencyTest(unittest.TestCase):
    def test_same_thread_lock_contention(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            home.mkdir()
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(SLOW_FAKE_CLAUDE, encoding="utf-8")
            fake_claude.chmod(0o755)

            results: list[int] = []

            def run_once() -> None:
                with mock.patch.dict(
                    os.environ,
                    {"HOME": str(home), "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude)},
                    clear=False,
                ), mock.patch("sys.stdout.write"), mock.patch("sys.stderr.write"):
                    results.append(main(["ask", "--prompt", "hello", "--workspace", str(workspace)]))

            first = threading.Thread(target=run_once)
            second = threading.Thread(target=run_once)
            first.start()
            time.sleep(0.05)
            second.start()
            first.join()
            second.join()

        self.assertEqual(sorted(results), [0, 3])


if __name__ == "__main__":
    unittest.main()
