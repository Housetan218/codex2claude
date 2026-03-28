import tempfile
import unittest
from pathlib import Path
from unittest import mock


class StatePersistenceTest(unittest.TestCase):
    def test_save_and_load_thread_state(self) -> None:
        from codex2claude.models import ThreadState
        from codex2claude.state import load_thread_state, save_thread_state

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "thread.json"
            state = ThreadState(
                thread_key="abc",
                workspace_root="/tmp/project",
                thread_name=None,
                claude_session_id=None,
                created_at="2026-03-28T00:00:00Z",
                last_used_at="2026-03-28T00:00:00Z",
                last_status="new",
                bridge_version="0.1.0",
                claude_version=None,
                last_error=None,
            )

            save_thread_state(path, state)
            loaded = load_thread_state(path)

        self.assertEqual(loaded.thread_key, "abc")

    def test_invalid_thread_state_shape_raises_state_error(self) -> None:
        from codex2claude.errors import StateCorruptionError
        from codex2claude.state import load_thread_state

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "thread.json"
            path.write_text('{"thread_key": "abc"}', encoding="utf-8")

            with self.assertRaises(StateCorruptionError):
                load_thread_state(path)

    def test_save_run_record_uses_replace(self) -> None:
        from codex2claude.models import RunRecord
        from codex2claude.state import save_run_record

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run.json"
            record = RunRecord(
                run_id="run-1",
                thread_key="thread-1",
                started_at="2026-03-28T00:00:00Z",
                ended_at="2026-03-28T00:00:01Z",
                duration_ms=1000,
                used_resume=False,
                prompt_sha256="abc",
                exit_code=0,
                parse_ok=True,
                stdout_preview="ok",
                stderr_preview="",
            )

            original_replace = Path.replace
            with mock.patch("pathlib.Path.replace", autospec=True, side_effect=original_replace) as replace_mock:
                save_run_record(path, record)

        self.assertTrue(replace_mock.called)


if __name__ == "__main__":
    unittest.main()
