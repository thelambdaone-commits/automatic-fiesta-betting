import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from check_setup import _redact, format_results


class CheckSetupTest(unittest.TestCase):
    def test_redact_hides_secret_middle(self):
        self.assertEqual(_redact("1234567890abcdef"), "1234...cdef")

    def test_format_results_marks_status(self):
        text = format_results([
            {"name": "rpc", "ok": True, "detail": "block=1"},
            {"name": "ws", "ok": False, "detail": "bad url"},
        ])
        self.assertIn("OK rpc: block=1", text)
        self.assertIn("FAIL ws: bad url", text)


if __name__ == "__main__":
    unittest.main()
