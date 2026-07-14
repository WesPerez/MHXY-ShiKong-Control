"""Regression coverage for source-of-truth workflow readiness auditing."""

from pathlib import Path
import unittest

import audit_workflow_readiness as readiness


ROOT = Path(__file__).resolve().parents[1]


class WorkflowReadinessAuditTests(unittest.TestCase):
    def test_imported_home_vitality_blueprint_is_counted_with_its_steps(self) -> None:
        main_source = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
        home_source = (ROOT / "src" / "home-vitality-core.js").read_text(encoding="utf-8")
        blueprints = readiness.parse_blueprints(
            main_source,
            {"HOME_VITALITY_BLUEPRINT": readiness.parse_home_vitality_blueprint(home_source)},
        )
        home = next(item for item in blueprints if item["id"] == "home-vitality")
        self.assertGreaterEqual(len(home["steps"]), 10)

    def test_repository_readiness_audit_passes(self) -> None:
        result = readiness.audit(ROOT)
        self.assertTrue(result["passed"], result["failures"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
