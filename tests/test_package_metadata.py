from pathlib import Path
import unittest


class PackageMetadataTest(unittest.TestCase):
    def test_pyproject_exists(self) -> None:
        self.assertTrue(Path("pyproject.toml").exists())


if __name__ == "__main__":
    unittest.main()
