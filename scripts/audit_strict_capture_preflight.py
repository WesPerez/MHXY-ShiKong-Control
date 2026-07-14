#!/usr/bin/env python3
"""Audit the dedicated zero-input strict capture preflight boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def require(failures: list[str], source: str, token: str, message: str) -> None:
    if token not in source:
        failures.append(message)


def audit(project_root: Path) -> dict[str, object]:
    probe_path = project_root / "src-tauri" / "src" / "bin" / "strict_capture_probe.rs"
    verifier_path = project_root / "scripts" / "verify_strict_capture_preflight.py"
    binary_test_path = project_root / "scripts" / "test_strict_capture_probe_binary.py"
    progress_path = project_root / "scripts" / "execution_progress.py"
    state_audit_path = project_root / "scripts" / "audit_execution_state.py"
    package_path = project_root / "package.json"
    failures: list[str] = []

    for path, label in [
        (probe_path, "strict capture probe"),
        (verifier_path, "strict capture preflight verifier"),
        (binary_test_path, "strict capture probe binary test"),
    ]:
        if not path.is_file():
            failures.append("{} is missing".format(label))
    if failures:
        return {"passed": False, "failures": failures, "counts": {}}

    probe = probe_path.read_text(encoding="utf-8")
    verifier = verifier_path.read_text(encoding="utf-8")
    binary_test = binary_test_path.read_text(encoding="utf-8")
    progress = progress_path.read_text(encoding="utf-8")
    state_audit = state_audit_path.read_text(encoding="utf-8")
    package = json.loads(package_path.read_text(encoding="utf-8"))

    for token, message in [
        ("capture_client_rgb_strict", "probe must use strict HWND capture"),
        ("apply_health_to_captured_frame", "probe must apply capture health checks"),
        ("Some(target.client_width)", "probe must bind capture dimensions to the target window"),
        ("None,", "probe must not treat equal hashes as stale during a static wait-image observation"),
        ("match_template_budgeted", "probe must reuse bounded template matching"),
        ("Some(args.roi)", "probe must require an explicit bounded ROI"),
        ("input_sent: false", "probe must explicitly report zero input"),
        ("frame_hash_repeated_from_previous", "probe must record repeated hashes without treating them as input evidence"),
        ("verify_same_target", "probe must recheck target identity between samples"),
        ("capture_with_verified_target", "probe must recheck target identity after each capture"),
    ]:
        require(failures, probe, token, message)
    for forbidden in [
        "post_hotkey",
        "post_mouse_click",
        "post_mouse_double_click",
        "post_text",
        "Set" + "ForegroundWindow",
        "Get" + "ProcAddress",
        "Load" + "LibraryA",
        "Load" + "LibraryW",
    ]:
        if forbidden in probe:
            failures.append("probe must not reference input or foreground API {}".format(forbidden))

    for token, message in [
        ("imported_symbols", "binary test must inspect final PE imports"),
        ("BANNED_IMPORTS", "binary test must define prohibited input imports"),
        ("cargo", "binary test must compile the probe before inspection"),
        ("forbiddenInputImports=0", "binary test must report a clean input import table"),
    ]:
        require(failures, binary_test, token, message)

    for token, message in [
        ("VERIFIER_NAME = \"strict-capture-preflight-v1\"", "verifier must use a stable allowlisted name"),
        ("category=\"live_preflight\"", "verifier must record live_preflight evidence"),
        ("input_sent=False", "verifier must record zero input"),
        ("current_window_evidence", "verifier must require current window identity evidence"),
        ("GAME_CLIENT_ROLE", "verifier must require game-client window evidence"),
        ("GAME_CLIENT_PROCESS", "verifier must require the expected game process"),
        ("window evidence is stale", "verifier must reject stale window evidence"),
        ("staleAfterSeconds", "verifier must enforce the window observation TTL"),
        ("refreshed_window_record = current_window_evidence", "verifier must revalidate identity after probe execution"),
        ("probeGitBinding", "verifier must bind the probe report to one source workspace"),
        ("source workspace changed while the strict capture probe was running", "verifier must reject source drift during probing"),
        ("template path does not match", "verifier must bind probe output to the requested template"),
        ("ROI does not match", "verifier must bind probe output to the requested ROI"),
        ("threshold does not match", "verifier must bind probe output to the requested threshold"),
        ("validate_probe_report", "verifier must validate structured strict capture output"),
        ("wait_image did not meet its template threshold", "verifier must reject an unmatched wait_image"),
        ("subprocess.run", "verifier must invoke the narrow Rust probe without a shell"),
        ("shell=False", "verifier must keep probe execution shell-free"),
        ("\"--locked\"", "verifier must not let cargo rewrite the dependency lockfile"),
    ]:
        require(failures, verifier, token, message)

    for token, message in [
        ("live_preflight", "execution progress must classify live_preflight explicitly"),
        ("strict-capture-preflight-v1", "execution progress must allowlist only the strict preflight verifier"),
        ("passed live_preflight evidence must explicitly report inputSent=false", "execution progress must require explicit zero-input preflight evidence"),
        ("expected_git_binding", "execution progress must reject verifier evidence after source drift"),
        ("expected_criterion_binding", "execution progress must reject verifier evidence after active slice drift"),
    ]:
        require(failures, progress, token, message)
    for token, message in [
        ("live_preflight", "execution-state audit must validate preflight evidence"),
        ("must explicitly report inputSent=false", "execution-state audit must require explicit zero-input preflight evidence"),
    ]:
        require(failures, state_audit, token, message)

    scripts = package.get("scripts", {})
    if scripts.get("test:strict-capture-preflight") != "python -B scripts/test_verify_strict_capture_preflight.py":
        failures.append("package.json must expose strict capture preflight unit tests")
    if "npm run test:strict-capture-preflight" not in scripts.get("test:all-core", ""):
        failures.append("test:all-core must include strict capture preflight unit tests")
    if scripts.get("test:strict-capture-probe-binary") != "python -B scripts/test_strict_capture_probe_binary.py":
        failures.append("package.json must expose strict capture probe binary tests")
    if "npm run test:strict-capture-probe-binary" not in scripts.get("test:all-core", ""):
        failures.append("test:all-core must compile and inspect the strict capture probe binary")
    if scripts.get("audit:strict-capture-preflight") != "python -B scripts/audit_strict_capture_preflight.py":
        failures.append("package.json must expose strict capture preflight audit")
    if "npm run audit:strict-capture-preflight" not in scripts.get("audit:all", ""):
        failures.append("audit:all must include strict capture preflight audit")

    return {
        "passed": not failures,
        "failures": failures,
        "counts": {
            "probeInputApiReferences": sum(probe.count(token) for token in ["post_hotkey", "post_mouse_click", "post_mouse_double_click", "post_text"]),
            "probeStrictCaptureReferences": probe.count("capture_client_rgb_strict"),
            "preflightAllowlistReferences": progress.count("strict-capture-preflight-v1"),
        },
    }


def main() -> int:
    result = audit(Path(__file__).resolve().parents[1])
    for key, value in result["counts"].items():
        print("{}={}".format(key, value))
    for failure in result["failures"]:
        print("FAIL {}".format(failure))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
