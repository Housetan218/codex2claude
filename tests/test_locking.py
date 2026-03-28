import tempfile
import unittest
from pathlib import Path


class LockingTest(unittest.TestCase):
    def test_second_lock_attempt_fails(self) -> None:
        from codex2claude.locking import LockConflictError, acquire_thread_lock

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "thread.lock"
            with acquire_thread_lock(path):
                with self.assertRaises(LockConflictError):
                    with acquire_thread_lock(path):
                        pass


if __name__ == "__main__":
    unittest.main()
