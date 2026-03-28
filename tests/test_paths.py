import os
import unittest
from unittest import mock


class PathsTest(unittest.TestCase):
    def test_thread_file_path_uses_bridge_root(self) -> None:
        with mock.patch.dict(os.environ, {"HOME": "/tmp/codex2claude-home"}, clear=False):
            from codex2claude.paths import thread_file_path

            path = thread_file_path("abc123")

        self.assertIn("codex2claude", str(path))
        self.assertEqual(path.name, "abc123.json")

    def test_bridge_root_honors_override_env_var(self) -> None:
        with mock.patch.dict(os.environ, {"CODEX2CLAUDE_HOME": "/tmp/c2c-state-root"}, clear=False):
            from codex2claude.paths import bridge_root

            root = bridge_root()

        self.assertEqual(str(root), "/tmp/c2c-state-root")


if __name__ == "__main__":
    unittest.main()
