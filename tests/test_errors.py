from __future__ import annotations

import re
import unittest

from labcim_manager.errors import safe_exception_message


class SafeErrorTests(unittest.TestCase):
    def test_user_message_hides_exception_and_logs_reference(self) -> None:
        secret_detail = "postgresql://user:secret@example.invalid/labcim"
        error = RuntimeError(secret_detail)
        with self.assertLogs("labcim_manager", level="ERROR") as captured:
            message = safe_exception_message(error, context="teste")

        self.assertNotIn(secret_detail, message)
        match = re.search(r"Referência: ([0-9a-f]{12})", message)
        self.assertIsNotNone(match)
        self.assertIn(secret_detail, "\n".join(captured.output))
        self.assertIn(match.group(1), "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
