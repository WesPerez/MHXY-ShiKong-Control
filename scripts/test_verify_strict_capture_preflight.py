"""Regression coverage for zero-input strict capture preflight policy."""

from pathlib import Path
import tempfile
import unittest

import verify_strict_capture_preflight as verifier


def make_state() -> dict:
    return {
        "git": {
            "observedHead": "abc123",
            "workingTreeFingerprint": "sha256:workspace",
        },
        "runtime": {"staleAfterSeconds": 300},
        "activeSlice": {
            "id": "P4-S3",
            "acceptanceCriteria": [
                {"id": "P4-S3-C1", "requiredEvidenceCategories": ["live_preflight"]}
            ]
        },
    }


def make_window_record() -> dict:
    return {
        "id": "EVD-WINDOW",
        "capturedAt": verifier.utc_now(),
        "category": "window_identity",
        "status": "passed",
        "targetIdentity": "game-client:42@MyGame_x64r.exe:88",
        "provenance": {
            "captureMethod": "specialized_verifier",
            "runnerProfile": None,
            "verifier": "window-identity-v1",
        },
        "safety": {"windowIdentityVerified": True},
        "verification": {
            "role": "game-client",
            "processName": "MyGame_x64r.exe",
            "targetIdentity": "game-client:42@MyGame_x64r.exe:88",
        },
        "windowIdentity": {
            "hwnd": 88,
            "pid": 42,
            "title": "Dream Game",
            "process": "MyGame_x64r.exe",
            "clientWidth": 1280,
            "clientHeight": 720,
            "privilege": "same",
        },
        "git": {
            "observedHead": "abc123",
            "workingTreeFingerprint": "sha256:workspace",
        },
    }


def make_probe_report() -> dict:
    sample = {
        "frameHash": "fnv1a64:abc",
        "frameHashRepeatedFromPrevious": False,
        "captureProvider": "window_print",
        "captureReliability": "health_verified",
        "fallbackUsed": False,
        "strictTargetSource": True,
        "controlEligible": True,
        "matched": True,
        "matchBox": {"x": 10, "y": 20, "width": 30, "height": 40, "score": 0.95},
    }
    second = dict(sample, frameHashRepeatedFromPrevious=True)
    return {
        "kind": "mhxy-shikong.strict-capture-preflight",
        "version": 1,
        "inputSent": False,
        "templatePath": "C:/repo/assets/resource/ShiKong/templates/entry.png",
        "roi": {"x": 10, "y": 20, "width": 30, "height": 40},
        "target": {
            "hwnd": 88,
            "pid": 42,
            "title": "Dream Game",
            "processName": "MyGame_x64r.exe",
            "clientWidth": 1280,
            "clientHeight": 720,
        },
        "samples": [sample, second],
        "waitImage": {"action": "match_only", "matched": True, "threshold": 0.86, "sampleCount": 2},
    }


class StrictCapturePreflightTests(unittest.TestCase):
    def test_accepts_only_active_live_preflight_criterion(self) -> None:
        self.assertEqual(verifier.preflight_evidence_criteria(make_state(), "P4-S3-C1"), ["P4-S3-C1"])
        with self.assertRaises(RuntimeError):
            verifier.preflight_evidence_criteria(make_state(), "P4-S3-C2")

    def test_requires_current_allowlisted_window_evidence(self) -> None:
        state = make_state()
        record = make_window_record()
        self.assertEqual(
            verifier.current_window_evidence(state, "EVD-WINDOW", [record]), record
        )
        record["git"]["workingTreeFingerprint"] = "sha256:stale"
        with self.assertRaises(RuntimeError):
            verifier.current_window_evidence(state, "EVD-WINDOW", [record])

    def test_rejects_expired_window_evidence(self) -> None:
        state = make_state()
        record = make_window_record()
        record["capturedAt"] = "2000-01-01T00:00:00Z"
        with self.assertRaises(RuntimeError):
            verifier.current_window_evidence(state, "EVD-WINDOW", [record])

    def test_rejects_non_game_window_evidence(self) -> None:
        state = make_state()
        record = make_window_record()
        record["verification"]["role"] = "controller-app"
        with self.assertRaises(RuntimeError):
            verifier.current_window_evidence(state, "EVD-WINDOW", [record])
        record = make_window_record()
        record["windowIdentity"]["process"] = "mhxy-shikong-control.exe"
        with self.assertRaises(RuntimeError):
            verifier.current_window_evidence(state, "EVD-WINDOW", [record])

    def test_criterion_binding_tracks_the_active_slice(self) -> None:
        state = make_state()
        binding = verifier.preflight_criterion_binding(state, "P4-S3-C1")
        self.assertEqual(binding["sliceId"], "P4-S3")
        state["activeSlice"]["id"] = "P4-S4"
        self.assertNotEqual(
            verifier.preflight_criterion_binding(state, "P4-S3-C1"), binding
        )

    def test_template_stays_inside_asset_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="strict-capture-template-") as temp:
            root = Path(temp)
            template = root / "assets" / "resource" / "ShiKong" / "templates" / "entry.png"
            template.parent.mkdir(parents=True)
            template.write_bytes(b"fixture")
            self.assertEqual(verifier.resolve_template_path(str(template), root), template.resolve())
            outside = root / "outside.png"
            outside.write_bytes(b"fixture")
            with self.assertRaises(RuntimeError):
                verifier.resolve_template_path(str(outside), root)

    def test_repeated_frame_hash_is_observed_not_rejected(self) -> None:
        summary = verifier.validate_probe_report(
            make_probe_report(),
            make_window_record(),
            Path("C:/repo/assets/resource/ShiKong/templates/entry.png"),
            (10, 20, 30, 40),
            0.86,
            2,
        )
        self.assertTrue(summary["matched"])
        self.assertTrue(summary["repeatedHashesObserved"])
        self.assertFalse(summary["inputSent"])

    def test_rejects_probe_parameter_mismatch(self) -> None:
        report = make_probe_report()
        report["roi"]["width"] = 31
        with self.assertRaises(RuntimeError):
            verifier.validate_probe_report(
                report,
                make_window_record(),
                Path("C:/repo/assets/resource/ShiKong/templates/entry.png"),
                (10, 20, 30, 40),
                0.86,
                2,
            )

    def test_probe_command_has_no_input_switch(self) -> None:
        command = verifier.build_probe_command(
            88,
            Path("C:/repo/assets/resource/ShiKong/templates/entry.png"),
            (10, 20, 30, 40),
            0.86,
            2,
            250,
        )
        self.assertIn("strict_capture_probe", command)
        self.assertIn("--locked", command)
        self.assertNotIn("--allow-input", command)
        self.assertNotIn("--input", command)


if __name__ == "__main__":
    unittest.main(verbosity=2)
