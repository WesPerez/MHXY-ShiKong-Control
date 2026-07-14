"""Regression coverage for the runtime-lane static audit source mapping."""

from pathlib import Path
import unittest

import audit_runtime_lane


ROOT = Path(__file__).resolve().parents[1]


class RuntimeLaneAuditTests(unittest.TestCase):
    def test_repository_runtime_lane_audit_passes(self) -> None:
        result = audit_runtime_lane.audit(ROOT)
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreaterEqual(result["counts"]["templateCheckpointTests"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
