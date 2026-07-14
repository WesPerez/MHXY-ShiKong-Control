#!/usr/bin/env python3
"""Verify a bounded, zero-input wait_image observation from a strict HWND capture."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import execution_progress as progress


VERIFIER_NAME = "strict-capture-preflight-v1"
PROBE_MARKER = "STRICT_CAPTURE_PROBE_JSON="
INPUT_ELIGIBLE_PRIVILEGES = {"same", "elevated"}
GAME_CLIENT_ROLE = "game-client"
GAME_CLIENT_PROCESS = "mygame_x64r.exe"
TEMPLATE_ROOT = progress.ROOT / "assets" / "resource" / "ShiKong"
ALLOWED_TEMPLATE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def report_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def preflight_criterion_binding(state: Dict[str, Any], criterion_id: str, supporting_only: bool = False) -> Dict[str, Any]:
    active_slice = state.get("activeSlice") or {}
    slice_id = active_slice.get("id")
    if not isinstance(slice_id, str) or not slice_id:
        raise RuntimeError("strict capture preflight requires an active slice id")
    if supporting_only:
        if active_slice.get("status") != "in_progress":
            raise RuntimeError("supporting-only live_preflight requires an in_progress active slice")
        return {
            "sliceId": slice_id,
            "criterionId": None,
            "requiredEvidenceCategories": ["live_preflight"],
            "supportingOnly": True,
        }
    active_criteria = {
        item.get("id"): item for item in active_slice.get("acceptanceCriteria", [])
    }
    criterion = active_criteria.get(criterion_id)
    required_categories = criterion.get("requiredEvidenceCategories", []) if criterion else []
    if (
        not criterion
        or not isinstance(required_categories, list)
        or not all(isinstance(category, str) for category in required_categories)
        or "live_preflight" not in required_categories
    ):
        raise RuntimeError("criterion is not an active live_preflight acceptance criterion")
    return {
        "sliceId": slice_id,
        "criterionId": criterion_id,
        "requiredEvidenceCategories": sorted(required_categories),
    }


def preflight_evidence_criteria(state: Dict[str, Any], criterion_id: str, supporting_only: bool = False) -> List[str]:
    binding = preflight_criterion_binding(state, criterion_id, supporting_only=supporting_only)
    if binding.get("supportingOnly"):
        return []
    return [criterion_id]


def current_git_binding(state: Dict[str, Any]) -> Dict[str, str]:
    state_git = state.get("git") or {}
    snapshot = progress.current_git_snapshot()
    observed_head = state_git.get("observedHead")
    fingerprint = state_git.get("workingTreeFingerprint")
    if not observed_head or not fingerprint:
        raise RuntimeError("execution state lacks a current source binding")
    if (
        snapshot.get("observedHead") != observed_head
        or snapshot.get("workingTreeFingerprint") != fingerprint
    ):
        raise RuntimeError("source workspace changed before strict capture preflight")
    return {
        "observedHead": observed_head,
        "workingTreeFingerprint": fingerprint,
    }


def parse_roi(value: str) -> Tuple[int, int, int, int]:
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 4:
        raise RuntimeError("--roi must use x,y,width,height")
    try:
        roi = tuple(int(item) for item in parts)
    except ValueError as exc:
        raise RuntimeError("--roi must contain integers") from exc
    if any(item < 0 for item in roi) or roi[2] <= 0 or roi[3] <= 0:
        raise RuntimeError("--roi requires non-negative x/y and positive width/height")
    return roi


def resolve_template_path(raw_path: str, root: Path = progress.ROOT) -> Path:
    candidate = Path(raw_path)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    template_root = (root / "assets" / "resource" / "ShiKong").resolve()
    try:
        path.relative_to(template_root)
    except ValueError as exc:
        raise RuntimeError("template must remain under assets/resource/ShiKong") from exc
    if path.suffix.lower() not in ALLOWED_TEMPLATE_SUFFIXES:
        raise RuntimeError("template must be a png, jpg, jpeg, or bmp image")
    if not path.is_file():
        raise RuntimeError("template image is missing: {}".format(path))
    return path


def current_window_evidence(
    state: Dict[str, Any], evidence_id: str, records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    record = next((item for item in records if item.get("id") == evidence_id), None)
    if not record:
        raise RuntimeError("window identity evidence does not exist: {}".format(evidence_id))
    if record.get("category") != "window_identity" or record.get("status") != "passed":
        raise RuntimeError("window evidence must be passed window_identity evidence")
    if not progress.evidence_provenance_valid(record):
        raise RuntimeError("window evidence lacks an allowlisted specialized verifier")
    if not record.get("safety", {}).get("windowIdentityVerified"):
        raise RuntimeError("window evidence does not verify its target identity")
    if not record.get("targetIdentity"):
        raise RuntimeError("window evidence lacks targetIdentity")
    identity = record.get("windowIdentity") or {}
    required = [
        identity.get("hwnd"),
        identity.get("pid"),
        identity.get("title"),
        identity.get("process"),
        identity.get("clientWidth"),
        identity.get("clientHeight"),
    ]
    if any(value in {None, ""} for value in required):
        raise RuntimeError("window evidence lacks required HWND identity fields")
    verification = record.get("verification")
    if not isinstance(verification, dict) or verification.get("role") != GAME_CLIENT_ROLE:
        raise RuntimeError("window evidence must verify a game-client role")
    if str(identity.get("process", "")).casefold() != GAME_CLIENT_PROCESS:
        raise RuntimeError("window evidence must verify the MyGame_x64r.exe process")
    if str(verification.get("processName", "")).casefold() != GAME_CLIENT_PROCESS:
        raise RuntimeError("window verification process does not match MyGame_x64r.exe")
    if verification.get("targetIdentity") != record.get("targetIdentity"):
        raise RuntimeError("window verification target identity does not match its evidence record")
    if identity.get("privilege") not in INPUT_ELIGIBLE_PRIVILEGES:
        raise RuntimeError("window evidence privilege is not eligible for future gated input")
    state_git = state.get("git") or {}
    evidence_git = record.get("git") or {}
    if (
        evidence_git.get("observedHead") != state_git.get("observedHead")
        or evidence_git.get("workingTreeFingerprint") != state_git.get("workingTreeFingerprint")
    ):
        raise RuntimeError("window evidence is stale for the current source workspace")
    captured_at = record.get("capturedAt")
    try:
        observed_at = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("window evidence lacks a valid observation timestamp") from exc
    stale_after_seconds = int((state.get("runtime") or {}).get("staleAfterSeconds", 300))
    if stale_after_seconds < 1:
        raise RuntimeError("runtime staleAfterSeconds is invalid")
    age_seconds = (datetime.now(timezone.utc) - observed_at).total_seconds()
    if age_seconds < -5 or age_seconds > stale_after_seconds:
        raise RuntimeError("window evidence is stale for strict capture preflight")
    return record


def build_probe_command(
    hwnd: int,
    template_path: Path,
    roi: Tuple[int, int, int, int],
    threshold: float,
    samples: int,
    interval_ms: int,
) -> List[str]:
    return [
        "cargo",
        "run",
        "--quiet",
        "--locked",
        "--manifest-path",
        str(progress.ROOT / "src-tauri" / "Cargo.toml"),
        "--bin",
        "strict_capture_probe",
        "--",
        "--hwnd",
        str(hwnd),
        "--template",
        str(template_path),
        "--roi",
        ",".join(str(value) for value in roi),
        "--threshold",
        "{:.6f}".format(threshold),
        "--samples",
        str(samples),
        "--interval-ms",
        str(interval_ms),
    ]


def parse_probe_output(output: str) -> Dict[str, Any]:
    for line in reversed(output.splitlines()):
        if line.startswith(PROBE_MARKER):
            try:
                parsed = json.loads(line[len(PROBE_MARKER) :])
            except json.JSONDecodeError as exc:
                raise RuntimeError("strict capture probe returned malformed JSON") from exc
            if not isinstance(parsed, dict):
                raise RuntimeError("strict capture probe returned a non-object report")
            return parsed
    raise RuntimeError("strict capture probe did not return a structured report")


def validate_probe_report(
    report: Dict[str, Any],
    window_record: Dict[str, Any],
    template_path: Path,
    roi: Tuple[int, int, int, int],
    threshold: float,
    samples_requested: int,
) -> Dict[str, Any]:
    if report.get("kind") != "mhxy-shikong.strict-capture-preflight" or report.get("version") != 1:
        raise RuntimeError("strict capture probe report has an unexpected schema")
    if report.get("inputSent") is not False:
        raise RuntimeError("strict capture probe must never report inputSent")
    try:
        reported_template = Path(str(report.get("templatePath", ""))).resolve()
    except OSError as exc:
        raise RuntimeError("strict capture probe template path is invalid") from exc
    if reported_template != template_path.resolve():
        raise RuntimeError("strict capture probe template path does not match the requested template")
    expected_roi = {"x": roi[0], "y": roi[1], "width": roi[2], "height": roi[3]}
    if report.get("roi") != expected_roi:
        raise RuntimeError("strict capture probe ROI does not match the requested ROI")

    expected = window_record.get("windowIdentity") or {}
    actual = report.get("target") or {}

    def _norm_process_name(value):
        text = str(value or "").strip()
        if text.lower().endswith(".exe"):
            text = text[:-4]
        return text.casefold()

    for key, expected_value in [
        ("hwnd", expected.get("hwnd")),
        ("pid", expected.get("pid")),
        ("title", expected.get("title")),
        ("processName", expected.get("process")),
        ("clientWidth", expected.get("clientWidth")),
        ("clientHeight", expected.get("clientHeight")),
    ]:
        actual_value = actual.get(key)
        if key == "processName":
            if _norm_process_name(actual_value) != _norm_process_name(expected_value):
                raise RuntimeError("strict capture probe target processName does not match window evidence")
            continue
        if actual_value != expected_value:
            raise RuntimeError("strict capture probe target {} does not match window evidence".format(key))

    samples = report.get("samples")
    if not isinstance(samples, list) or len(samples) != samples_requested:
        raise RuntimeError("strict capture probe sample count does not match the request")
    for sample in samples:
        if not isinstance(sample, dict):
            raise RuntimeError("strict capture probe sample is malformed")
        if sample.get("strictTargetSource") is not True or sample.get("controlEligible") is not True:
            raise RuntimeError("strict capture probe accepted an untrusted capture source")
        if sample.get("fallbackUsed") is not False:
            raise RuntimeError("strict capture probe must reject desktop fallback")
        if sample.get("captureProvider") not in {"window_print", "window_gdi"}:
            raise RuntimeError("strict capture probe used an unexpected capture provider")
        if sample.get("captureReliability") != "health_verified":
            raise RuntimeError("strict capture probe used a non-health-verified frame")
        if sample.get("matched") not in {True, False} or not isinstance(sample.get("matchBox"), dict):
            raise RuntimeError("strict capture probe lacks a match-only observation")
        score = sample["matchBox"].get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise RuntimeError("strict capture probe match score is invalid")
        if bool(sample["matched"]) != (float(score) >= threshold):
            raise RuntimeError("strict capture probe match result does not match the requested threshold")

    wait_image = report.get("waitImage") or {}
    if wait_image.get("action") != "match_only":
        raise RuntimeError("strict capture probe must use match_only wait_image behavior")
    if wait_image.get("matched") is not True:
        raise RuntimeError("zero-input wait_image did not meet its template threshold")
    if wait_image.get("sampleCount") != samples_requested:
        raise RuntimeError("strict capture probe wait_image sample count is inconsistent")
    wait_threshold = wait_image.get("threshold")
    if isinstance(wait_threshold, bool) or not isinstance(wait_threshold, (int, float)) or not math.isclose(float(wait_threshold), threshold, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError("strict capture probe wait_image threshold does not match the request")
    if not any(sample.get("matched") is True for sample in samples):
        raise RuntimeError("strict capture probe matched wait_image without a matching sample")
    return {
        "targetIdentity": window_record["targetIdentity"],
        "target": actual,
        "inputSent": False,
        "sampleCount": len(samples),
        "matched": True,
        "repeatedHashesObserved": any(sample.get("frameHashRepeatedFromPrevious") is True for sample in samples),
    }


def verify_strict_capture_preflight(
    criterion_id: str,
    window_evidence_id: str,
    template_path: Path,
    roi: Tuple[int, int, int, int],
    threshold: float,
    samples: int,
    interval_ms: int,
    supporting_only: bool = False,
) -> Dict[str, Any]:
    with progress.ProgressLock(progress.progress_lock_path()):
        state = progress.load_json(progress.STATE_PATH)
        progress.refresh_state_runtime_fields(state)
        probe_git_binding = current_git_binding(state)
        criterion_binding = preflight_criterion_binding(state, criterion_id, supporting_only=supporting_only)
        evidence_criteria = preflight_evidence_criteria(state, criterion_id, supporting_only=supporting_only)
        window_record = current_window_evidence(
            state, window_evidence_id, progress.load_jsonl(progress.EVIDENCE_PATH)
        )

    identity = window_record["windowIdentity"]
    command = build_probe_command(
        int(identity["hwnd"]), template_path, roi, threshold, samples, interval_ms
    )
    completed = subprocess.run(
        command,
        cwd=str(progress.ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "strict capture probe failed with exit code {}: {}".format(
                completed.returncode, completed.stdout.strip()
            )
        )
    probe_report = parse_probe_output(completed.stdout)
    # Cargo can spend long enough compiling a cold target that the identity proof
    # becomes stale after the initial check. Revalidate it before creating evidence.
    with progress.ProgressLock(progress.progress_lock_path()):
        state = progress.load_json(progress.STATE_PATH)
        progress.refresh_state_runtime_fields(state)
        if current_git_binding(state) != probe_git_binding:
            raise RuntimeError("source workspace changed while the strict capture probe was running")
        if preflight_criterion_binding(state, criterion_id, supporting_only=supporting_only) != criterion_binding:
            raise RuntimeError("active live_preflight criterion changed while the strict capture probe was running")
        refreshed_window_record = current_window_evidence(
            state, window_evidence_id, progress.load_jsonl(progress.EVIDENCE_PATH)
        )
        if refreshed_window_record.get("targetIdentity") != window_record.get("targetIdentity"):
            raise RuntimeError("window identity changed while the strict capture probe was running")
        window_record = refreshed_window_record
    summary = validate_probe_report(
        probe_report,
        window_record,
        template_path,
        roi,
        threshold,
        samples,
    )
    command_text = subprocess.list2cmdline(command)

    report_dir = (
        progress.ROOT
        / "assets"
        / "resource"
        / "ShiKong"
        / "reports"
        / "dev-progress"
        / "strict-capture-preflight-{}-{}".format(criterion_id, report_stamp())
    )
    report_dir.mkdir(parents=True, exist_ok=False)
    report_path = report_dir / "preflight-report.json"
    verification = {
        "verifier": VERIFIER_NAME,
        "criterionId": criterion_id,
        "windowEvidenceId": window_evidence_id,
        "targetIdentity": window_record["targetIdentity"],
        "windowIdentity": identity,
        "templatePath": str(template_path.relative_to(progress.ROOT)).replace("\\", "/"),
        "roi": {"x": roi[0], "y": roi[1], "width": roi[2], "height": roi[3]},
        "threshold": threshold,
        "samples": samples,
        "intervalMs": interval_ms,
        "inputSent": False,
        "probe": probe_report,
        "summary": summary,
        "observedHead": probe_git_binding["observedHead"],
        "workingTreeFingerprint": probe_git_binding["workingTreeFingerprint"],
        "probeGitBinding": probe_git_binding,
        "createdAt": utc_now(),
    }
    report_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    evidence_args = argparse.Namespace(
        id=None,
        category="live_preflight",
        claim="Strict target capture completed bounded zero-input wait_image preflight",
        status="passed",
        command=command_text,
        target_identity=window_record["targetIdentity"],
        window_evidence_id=window_evidence_id,
        window_hwnd=identity["hwnd"],
        window_pid=identity["pid"],
        window_title=identity["title"],
        window_process=identity["process"],
        client_width=identity["clientWidth"],
        client_height=identity["clientHeight"],
        privilege=identity["privilege"],
        exit_code=0,
        criterion=evidence_criteria,
        artifact=[str(report_path.relative_to(progress.ROOT)).replace("\\", "/")],
        input_sent=False,
        foreground_unchanged=None,
        cursor_unchanged=None,
        window_identity_verified=True,
        postcondition_observed=True,
        capture_method="specialized_verifier",
        runner_profile=None,
        verifier=VERIFIER_NAME,
        verification=verification,
        expected_git_binding=probe_git_binding,
        expected_criterion_binding=None if supporting_only else criterion_binding,
    )
    evidence_id = progress.record_evidence(evidence_args, allow_passed=True)
    return {
        "evidenceId": evidence_id,
        "targetIdentity": window_record["targetIdentity"],
        "reportPath": str(report_path),
        "inputSent": False,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--criterion", required=False, default="SUPPORTING")
    parser.add_argument("--supporting-only", action="store_true")
    parser.add_argument("--window-evidence-id", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--roi", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--interval-ms", type=int, default=250)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not 0.0 <= args.threshold <= 1.0:
        raise RuntimeError("--threshold must be within 0..1")
    if not 2 <= args.samples <= 8:
        raise RuntimeError("--samples must be within 2..8")
    if not 50 <= args.interval_ms <= 5_000:
        raise RuntimeError("--interval-ms must be within 50..5000")
    result = verify_strict_capture_preflight(
        args.criterion,
        args.window_evidence_id,
        resolve_template_path(args.template),
        parse_roi(args.roi),
        args.threshold,
        args.samples,
        args.interval_ms,
        supporting_only=args.supporting_only,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result["evidenceId"])
        print(result["targetIdentity"])
        print(result["reportPath"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("strict capture preflight failed: {}".format(exc), file=sys.stderr)
        sys.exit(1)
