import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock, skipUnless


@skipUnless(shutil.which("claude"), "claude CLI missing")
class RealClaudeCliTest(unittest.TestCase):
    def test_real_claude_roundtrip_smoke(self) -> None:
        if os.environ.get("CODEX2CLAUDE_RUN_REAL") != "1":
            self.skipTest("set CODEX2CLAUDE_RUN_REAL=1 to enable real Claude integration")

        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            with mock.patch.dict(os.environ, {"CODEX2CLAUDE_HOME": str(state_root)}, clear=False), mock.patch("sys.stdout.write"):
                exit_code = main(["ask", "--prompt", "Reply with ok only", "--workspace", str(workspace), "--timeout", "120"])

        self.assertEqual(exit_code, 0)

    def test_real_claude_resume_smoke(self) -> None:
        if os.environ.get("CODEX2CLAUDE_RUN_REAL") != "1":
            self.skipTest("set CODEX2CLAUDE_RUN_REAL=1 to enable real Claude integration")

        from codex2claude.cli import main
        from codex2claude.threading import make_thread_key

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            with mock.patch.dict(os.environ, {"CODEX2CLAUDE_HOME": str(state_root)}, clear=False), mock.patch("sys.stdout.write"):
                first = main(["ask", "--prompt", "Reply with ok only", "--workspace", str(workspace), "--thread", "resume-smoke", "--timeout", "120"])
                second = main(["ask", "--prompt", "Now reply with resume-ok only", "--workspace", str(workspace), "--thread", "resume-smoke", "--timeout", "120"])

            thread_key = make_thread_key(str(workspace), "resume-smoke")
            run_files = sorted((state_root / "runs" / thread_key).glob("*.json"))
            last_record = json.loads(run_files[-1].read_text(encoding="utf-8"))

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)
        self.assertTrue(last_record["used_resume"])


if __name__ == "__main__":
    unittest.main()
