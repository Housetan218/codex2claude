import unittest


class ThreadKeyTest(unittest.TestCase):
    def test_thread_key_is_stable_for_same_workspace_and_name(self) -> None:
        from codex2claude.threading import make_thread_key

        a = make_thread_key("/tmp/project", None)
        b = make_thread_key("/tmp/project", None)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
