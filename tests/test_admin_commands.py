import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


class AdminCommandsTest(unittest.TestCase):
    def test_status_command_on_missing_thread_returns_nonzero(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}, clear=False):
                exit_code = main(["status", "--workspace", "/tmp/project"])

        self.assertNotEqual(exit_code, 0)

    def test_forget_command_removes_thread_file(self) -> None:
        from codex2claude.cli import main
        from codex2claude.threading import make_thread_key

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            workspace = Path(temp_dir) / "workspace"
            home.mkdir()
            workspace.mkdir()
            thread_key = make_thread_key(str(workspace), None)
            state_path = home / ".codex" / "codex2claude" / "threads" / f"{thread_key}.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "thread_key": thread_key,
                        "workspace_root": str(workspace),
                        "thread_name": None,
                        "claude_session_id": "session-123",
                        "created_at": "2026-03-28T00:00:00Z",
                        "last_used_at": "2026-03-28T00:00:00Z",
                        "last_status": "ok",
                        "bridge_version": "0.1.0",
                        "claude_version": "1.0.0",
                        "last_error": None,
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                exit_code = main(["forget", "--workspace", str(workspace)])

            self.assertEqual(exit_code, 0)
            self.assertFalse(state_path.exists())

    def test_gc_removes_old_thread_files(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir) / "home"
            threads_dir = home / ".codex" / "codex2claude" / "threads"
            home.mkdir()
            threads_dir.mkdir(parents=True)
            old_file = threads_dir / "old-thread.json"
            old_file.write_text("{}", encoding="utf-8")
            old_time = time.time() - (10 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))

            with mock.patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                exit_code = main(["gc", "--max-age-days", "7"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(old_file.exists())

    def test_gc_removes_old_run_directories_and_lock_files(self) -> None:
        from codex2claude.cli import main

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            threads_dir = state_root / "threads"
            runs_dir = state_root / "runs" / "old-thread"
            threads_dir.mkdir(parents=True)
            runs_dir.mkdir(parents=True)

            old_lock = threads_dir / "old-thread.lock"
            old_lock.write_text("", encoding="utf-8")
            old_run = runs_dir / "artifact.json"
            old_run.write_text("{}", encoding="utf-8")

            old_time = time.time() - (10 * 24 * 60 * 60)
            os.utime(old_lock, (old_time, old_time))
            os.utime(old_run, (old_time, old_time))
            os.utime(runs_dir, (old_time, old_time))

            with mock.patch.dict(os.environ, {"CODEX2CLAUDE_HOME": str(state_root)}, clear=False):
                exit_code = main(["gc", "--max-age-days", "7"])

            self.assertEqual(exit_code, 0)
            self.assertFalse(old_lock.exists())
            self.assertFalse(runs_dir.exists())

    def test_gc_skips_locked_threads(self) -> None:
        from codex2claude.cli import main
        from codex2claude.locking import acquire_thread_lock

        with tempfile.TemporaryDirectory() as temp_dir:
            state_root = Path(temp_dir) / "state"
            threads_dir = state_root / "threads"
            runs_dir = state_root / "runs" / "busy-thread"
            threads_dir.mkdir(parents=True)
            runs_dir.mkdir(parents=True)

            old_thread = threads_dir / "busy-thread.json"
            old_thread.write_text("{}", encoding="utf-8")
            old_lock = threads_dir / "busy-thread.lock"
            old_lock.write_text("", encoding="utf-8")
            old_run = runs_dir / "artifact.json"
            old_run.write_text("{}", encoding="utf-8")

            old_time = time.time() - (10 * 24 * 60 * 60)
            for path in (old_thread, old_lock, old_run, runs_dir):
                os.utime(path, (old_time, old_time))

            with mock.patch.dict(os.environ, {"CODEX2CLAUDE_HOME": str(state_root)}, clear=False):
                with acquire_thread_lock(old_lock):
                    exit_code = main(["gc", "--max-age-days", "7"])

            self.assertEqual(exit_code, 0)
            self.assertTrue(old_thread.exists())
            self.assertTrue(old_lock.exists())
            self.assertTrue(runs_dir.exists())


if __name__ == "__main__":
    unittest.main()
