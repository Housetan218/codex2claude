from pathlib import Path
import unittest


class SkillDocsTest(unittest.TestCase):
    def test_skill_file_exists(self) -> None:
        self.assertTrue(Path("skills/codex-to-claude/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
