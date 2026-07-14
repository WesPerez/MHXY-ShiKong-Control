"""Regression coverage for the strict capture preflight static audit."""

from pathlib import Path
import unittest

import audit_strict_capture_preflight


ROOT = Path(__file__).resolve().parents[1]


class StrictCapturePreflightAuditTests(unittest.TestCase):
    def test_repository_audit_passes(self) -> None:
        result = audit_strict_capture_preflight.audit(ROOT)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["counts"]["probeInputApiReferences"], 0)
        self.assertGreaterEqual(result["counts"]["probeStrictCaptureReferences"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
