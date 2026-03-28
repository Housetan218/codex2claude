import json
import os
import subprocess
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
    prompt = ""
    session_id = None
    if "-p" in args:
        prompt = args[args.index("-p") + 1]
    if "--resume" in args:
        session_id = args[args.index("--resume") + 1]

    payload = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": f"echo:{prompt}",
        "session_id": session_id or "new-session-123",
    }
    sys.stdout.write(json.dumps(payload))
    """
)


class AskFlowTest(unittest.TestCase):
    def test_ask_creates_thread_and_returns_success(self) -> None:
        from codex2claude.cli import main
        from codex2claude.threading import make_thread_key

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            home.mkdir()
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(FAKE_CLAUDE, encoding="utf-8")
            fake_claude.chmod(0o755)

            env = {"HOME": str(home), "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude)}
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write") as mock_write:
                exit_code = main(["ask", "--prompt", "hello", "--workspace", str(workspace)])
                thread_key = make_thread_key(str(workspace), None)
                state_path = home / ".codex" / "codex2claude" / "threads" / f"{thread_key}.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(mock_write.called)
        self.assertEqual(state["claude_session_id"], "new-session-123")

    def test_second_ask_resumes_existing_session(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            log_path = Path(temp_dir) / "claude-args.log"
            home.mkdir()
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import sys\n"
                f"log_path = {str(log_path)!r}\n"
                "args = sys.argv[1:]\n"
                "prompt = ''\n"
                "session_id = None\n"
                "if '-p' in args:\n"
                "    prompt = args[args.index('-p') + 1]\n"
                "if '--resume' in args:\n"
                "    session_id = args[args.index('--resume') + 1]\n"
                "with open(log_path, 'a', encoding='utf-8') as handle:\n"
                "    handle.write(' '.join(args) + '\\n')\n"
                "payload = {\n"
                "    'type': 'result',\n"
                "    'subtype': 'success',\n"
                "    'is_error': False,\n"
                "    'result': f'echo:{prompt}',\n"
                "    'session_id': session_id or 'new-session-123',\n"
                "}\n"
                "sys.stdout.write(json.dumps(payload))\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            env = {"HOME": str(home), "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude)}
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"):
                self.assertEqual(main(["ask", "--prompt", "one", "--workspace", str(workspace)]), 0)
                self.assertEqual(main(["ask", "--prompt", "two", "--workspace", str(workspace)]), 0)

            log_lines = [
                line
                for line in log_path.read_text(encoding="utf-8").strip().splitlines()
                if " --output-format json" in line
            ]

        self.assertEqual(len(log_lines), 2)
        self.assertNotIn("--resume", log_lines[0])
        self.assertIn("--resume", log_lines[1])

    def test_ask_records_nonzero_duration_in_run_artifact(self) -> None:
        from codex2claude.cli import main
        from codex2claude.threading import make_thread_key

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import sys\n"
                "import time\n"
                "time.sleep(0.05)\n"
                "prompt = sys.argv[sys.argv.index('-p') + 1]\n"
                "sys.stdout.write(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': prompt, 'session_id': 'duration-session'}))\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            env = {
                "CODEX2CLAUDE_HOME": str(state_root),
                "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"):
                exit_code = main(["ask", "--prompt", "hello", "--workspace", str(workspace)])

            thread_key = make_thread_key(str(workspace), None)
            run_files = sorted((state_root / "runs" / thread_key).glob("*.json"))
            record = json.loads(run_files[0].read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertGreater(record["duration_ms"], 0)

    def test_existing_claude_version_is_preserved_if_version_probe_fails(self) -> None:
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
            thread_path.write_text(
                json.dumps(
                    {
                        "thread_key": thread_key,
                        "workspace_root": str(workspace.resolve()),
                        "thread_name": None,
                        "claude_session_id": "old-session",
                        "created_at": "2026-03-28T00:00:00Z",
                        "last_used_at": "2026-03-28T00:00:01Z",
                        "last_status": "ok",
                        "bridge_version": "0.1.0",
                        "claude_version": "claude-old-version",
                        "last_error": None,
                    }
                ),
                encoding="utf-8",
            )

            env = {
                "CODEX2CLAUDE_HOME": str(state_root),
                "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"), mock.patch(
                "codex2claude.cli.read_claude_version", return_value=None
            ):
                exit_code = main(["ask", "--prompt", "hello", "--workspace", str(workspace)])

            state = json.loads(thread_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(state["claude_version"], "claude-old-version")

    def test_new_flag_forces_fresh_session(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            log_path = Path(temp_dir) / "claude-args.log"
            home.mkdir()
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import sys\n"
                f"log_path = {str(log_path)!r}\n"
                "args = sys.argv[1:]\n"
                "prompt = args[args.index('-p') + 1]\n"
                "session_id = args[args.index('--resume') + 1] if '--resume' in args else None\n"
                "with open(log_path, 'a', encoding='utf-8') as handle:\n"
                "    handle.write(' '.join(args) + '\\n')\n"
                "sys.stdout.write(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': prompt, 'session_id': session_id or 'fresh-session'}))\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            env = {"HOME": str(home), "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude)}
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"):
                self.assertEqual(main(["ask", "--prompt", "one", "--workspace", str(workspace)]), 0)
                self.assertEqual(main(["ask", "--prompt", "two", "--workspace", str(workspace), "--new"]), 0)

            log_lines = [
                line
                for line in log_path.read_text(encoding="utf-8").strip().splitlines()
                if " --output-format json" in line
            ]

        self.assertEqual(len(log_lines), 2)
        self.assertNotIn("--resume", log_lines[1])

    def test_workspace_is_used_as_claude_working_directory(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            workspace = Path(temp_dir) / "workspace"
            bin_dir = Path(temp_dir) / "bin"
            cwd_log = Path(temp_dir) / "cwd.log"
            workspace.mkdir()
            bin_dir.mkdir()
            fake_claude = bin_dir / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import os\n"
                "import sys\n"
                f"cwd_log = {str(cwd_log)!r}\n"
                "with open(cwd_log, 'a', encoding='utf-8') as handle:\n"
                "    handle.write(os.getcwd() + '\\n')\n"
                "if '--version' in sys.argv:\n"
                "    sys.stdout.write('fake-claude 1.0')\n"
                "    raise SystemExit(0)\n"
                "prompt = sys.argv[sys.argv.index('-p') + 1]\n"
                "sys.stdout.write(json.dumps({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': prompt, 'session_id': 'cwd-session'}))\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            env = {
                "CODEX2CLAUDE_HOME": str(state_root),
                "CODEX2CLAUDE_CLAUDE_BIN": str(fake_claude),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch("sys.stdout.write"):
                exit_code = main(["ask", "--prompt", "hello", "--workspace", str(workspace)])

            observed_cwds = cwd_log.read_text(encoding="utf-8").splitlines()

        self.assertEqual(exit_code, 0)
        self.assertIn(str(workspace.resolve()), observed_cwds)


if __name__ == "__main__":
    unittest.main()
