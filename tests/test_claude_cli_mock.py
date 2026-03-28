import json
import unittest


class ClaudeCliAdapterTest(unittest.TestCase):
    def test_build_claude_command_for_new_prompt(self) -> None:
        from codex2claude.claude_cli import build_claude_command

        cmd = build_claude_command(prompt="hello", session_id=None, claude_bin="claude")

        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertIn("--output-format", cmd)

    def test_parse_claude_success_response(self) -> None:
        from codex2claude.claude_cli import parse_claude_response

        payload = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "hello",
                "session_id": "session-123",
            }
        )

        result = parse_claude_response(payload)

        self.assertEqual(result.session_id, "session-123")
        self.assertEqual(result.result_text, "hello")

    def test_parse_claude_error_response_raises(self) -> None:
        from codex2claude.claude_cli import parse_claude_response
        from codex2claude.errors import ClaudeInvocationError

        payload = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": True,
                "result": "not logged in",
                "session_id": "session-123",
            }
        )

        with self.assertRaises(ClaudeInvocationError):
            parse_claude_response(payload)

    def test_parse_claude_empty_session_id_raises(self) -> None:
        from codex2claude.claude_cli import parse_claude_response
        from codex2claude.errors import StateCorruptionError

        payload = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "hello",
                "session_id": "",
            }
        )

        with self.assertRaises(StateCorruptionError):
            parse_claude_response(payload)


if __name__ == "__main__":
    unittest.main()
