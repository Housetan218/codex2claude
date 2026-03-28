import unittest


class VersionSmokeTest(unittest.TestCase):
    def test_version_is_defined(self) -> None:
        from codex2claude.version import __version__

        self.assertIsInstance(__version__, str)
        self.assertTrue(__version__)


if __name__ == "__main__":
    unittest.main()
