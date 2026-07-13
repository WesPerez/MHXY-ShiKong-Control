#!/usr/bin/env python3
"""Create and verify one non-overwriting P0 workspace backup."""

from __future__ import print_function

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict

import execution_progress as progress


VERIFIER_NAME = "p0-workspace-backup-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def copy_exclusive(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(chunk)
        writer.flush()
        import os
        os.fsync(writer.fileno())


def verify_and_copy(action_id: str, criterion_id: str, command_text: str) -> Dict[str, Any]:
    with progress.ProgressLock(progress.progress_lock_path()):
        state = progress.load_json(progress.STATE_PATH)
        action = state.get("inFlightAction")
        if not action or action.get("actionId") != action_id:
            raise RuntimeError("matching in-flight backup action not found")
        if action.get("kind") != "appdata_backup" or action.get("status") != "running":
            raise RuntimeError("backup verifier requires a running appdata_backup action")
        if action.get("ownerRunId") != state.get("run", {}).get("runId"):
            raise RuntimeError("backup action is not owned by the current run")
        lease_token = progress.load_action_token(action_id)
        progress.verify_external_action_lease(action_id, lease_token)
        identity = action.get("backupIdentity") or {}
        source_info = identity.get("source") or {}
        destination_info = identity.get("destination") or {}
        source = Path(str(source_info.get("path", "")))
        destination = Path(str(destination_info.get("path", "")))
        if not source.is_absolute() or not destination.is_absolute():
            raise RuntimeError("backup action lacks absolute structured paths")
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("backup source is missing or is a symlink")
        if destination.exists() or destination.is_symlink():
            raise RuntimeError("backup destination no longer satisfies the absent precondition")
        expected_sha256 = str(source_info.get("sha256", "")).upper()
        source_stat = source.stat()
        source_before = sha256(source)
        if source_before != expected_sha256:
            raise RuntimeError("backup source hash changed after intent")
        if source_stat.st_size != source_info.get("size") or source_stat.st_mtime_ns != source_info.get("modifiedAtNs"):
            raise RuntimeError("backup source file identity changed after intent")
        active_criteria = {item.get("id"): item for item in state.get("activeSlice", {}).get("acceptanceCriteria", [])}
        criterion = active_criteria.get(criterion_id)
        if not criterion or "appdata_backup" not in criterion.get("requiredEvidenceCategories", []):
            raise RuntimeError("criterion is not an active appdata_backup acceptance criterion")
        copy_exclusive(source, destination)
        source_after = sha256(source)
        destination_sha256 = sha256(destination)
        destination_size = destination.stat().st_size
        if source_after != source_before or destination_sha256 != source_before or destination_size != source_stat.st_size:
            raise RuntimeError("backup postcondition failed: source/destination identity mismatch")

    verification = {
        "actionId": action_id,
        "idempotencyKey": action.get("idempotencyKey"),
        "sourcePath": str(source),
        "destinationPath": str(destination),
        "sourceSha256Before": source_before,
        "sourceSha256After": source_after,
        "destinationSha256": destination_sha256,
        "sourceSize": source_stat.st_size,
        "destinationSize": destination_size,
        "destinationWasAbsentAtIntent": destination_info.get("existedAtIntent") is False,
    }
    evidence_args = argparse.Namespace(
        id=None,
        category="appdata_backup",
        claim="P0 workspace backup verified without overwriting the source or an existing destination",
        status="passed",
        command=command_text,
        target_identity=action.get("targetIdentity"),
        window_evidence_id=None,
        window_hwnd=None,
        window_pid=None,
        window_title=None,
        window_process=None,
        client_width=None,
        client_height=None,
        privilege=None,
        exit_code=0,
        criterion=[criterion_id],
        artifact=[str(destination)],
        input_sent=False,
        foreground_unchanged=None,
        cursor_unchanged=None,
        window_identity_verified=None,
        postcondition_observed=True,
        capture_method="specialized_verifier",
        runner_profile=None,
        verifier=VERIFIER_NAME,
        verification=verification,
    )
    evidence_id = progress.record_evidence(evidence_args, allow_passed=True)
    progress.command_action_finish(argparse.Namespace(
        action_id=action_id,
        status="succeeded",
        result=json.dumps(verification, ensure_ascii=False, sort_keys=True),
        verified_evidence_id=evidence_id,
    ))
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and verify one P0 AppData workspace backup")
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--criterion", required=True)
    args = parser.parse_args()
    command_text = subprocess.list2cmdline([sys.executable, str(Path(__file__).resolve())] + sys.argv[1:])
    result = verify_and_copy(args.action_id, args.criterion, command_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
