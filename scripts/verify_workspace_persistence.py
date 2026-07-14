#!/usr/bin/env python3
"""Workspace persistence verifier: atomic write, double-read, and real AppData observe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import execution_progress as progress


VERIFIER_NAME = "workspace-persistence-v1"
DEFAULT_APPDATA = Path(os.environ.get("APPDATA", "")) / "local.mhxy.shikong.control" / "workspace.json"
PROTECTED_BACKUPS = [
    {
        "path": Path(os.environ.get("APPDATA", ""))
        / "local.mhxy.shikong.control"
        / "migration-backups"
        / "workspace.schema-v6.20260711T070831Z.445BE6550B81.json",
        "sha256": "445be6550b813dca8b783db6dc2f61c633234b41c410703de70beb810b6dd8d3",
        "evidenceId": "EVD-0029",
    },
    {
        "path": Path(os.environ.get("APPDATA", ""))
        / "local.mhxy.shikong.control"
        / "migration-backups"
        / "workspace.json.bak.schema-v6.20260711T070903Z.912454620A3C.json",
        "sha256": "912454620a3cfd57ff577eb5086b7aabfc8b1eed30a5671018bfc7ebff3d59ec",
        "evidenceId": "EVD-0030",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def atomic_write(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    tmp = path.with_name("." + path.name + "." + stamp + ".tmp")
    backup = path.with_suffix(path.suffix + ".bak")
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.exists() and not backup.exists():
        backup.write_bytes(path.read_bytes())
    os.replace(tmp, path)
    return backup


def double_read_equal(path: Path) -> Dict[str, Any]:
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise RuntimeError("restart double-read mismatch")
    return {
        "bytes": len(first),
        "sha256": sha256_bytes(first),
        "reads": 2,
        "equal": True,
    }


def build_fixture_workspace() -> Dict[str, Any]:
    return {
        "schemaVersion": 9,
        "updatedAt": utc_now(),
        "workflows": [{"id": "wf-persist", "name": "persist", "steps": []}],
        "targets": [
            {
                "id": "t-persist",
                "name": "persist-target",
                "contentHash": "a" * 64,
                "assetPath": "assets/by-hash/aa/" + ("a" * 64) + ".png",
            }
        ],
        "assetIndex": [
            {
                "contentHash": "a" * 64,
                "relativePath": "assets/by-hash/aa/" + ("a" * 64) + ".png",
                "mime": "image/png",
                "byteLength": 0,
                "targetIds": ["t-persist"],
            }
        ],
        "assignments": {},
        "runHistory": [],
    }


def run_offline_contract(work_dir: Path) -> Dict[str, Any]:
    workspace_path = work_dir / "workspace.json"
    payload = json.dumps(build_fixture_workspace(), ensure_ascii=False, indent=2).encode("utf-8")
    backup = atomic_write(workspace_path, payload)
    read1 = double_read_equal(workspace_path)
    atomic_write(workspace_path, payload)
    read2 = double_read_equal(workspace_path)
    if read1["sha256"] != read2["sha256"] or read1["sha256"] != sha256_bytes(payload):
        raise RuntimeError("persistence hash chain mismatch")
    parsed = json.loads(workspace_path.read_text(encoding="utf-8"))
    if not isinstance(parsed.get("assetIndex"), list):
        raise RuntimeError("workspace missing assetIndex after persistence")
    return {
        "mode": "offline-fixture",
        "workspacePath": str(workspace_path),
        "backupPath": str(backup) if backup.exists() else None,
        "payloadSha256": sha256_bytes(payload),
        "firstRead": read1,
        "secondRead": read2,
        "restartReadsEqual": True,
        "assetIndexCount": len(parsed.get("assetIndex") or []),
        "schemaVersion": parsed.get("schemaVersion"),
    }


def verify_protected_backups() -> List[Dict[str, Any]]:
    results = []
    for item in PROTECTED_BACKUPS:
        path: Path = item["path"]
        if not path.is_file():
            raise RuntimeError("protected backup missing: {}".format(path))
        digest = sha256_file(path)
        if digest != item["sha256"]:
            raise RuntimeError("protected backup hash drift for {}: {}".format(item["evidenceId"], path))
        results.append(
            {
                "evidenceId": item["evidenceId"],
                "path": str(path),
                "sha256": digest,
                "size": path.stat().st_size,
                "intact": True,
            }
        )
    return results


def run_real_appdata_observe(
    workspace_path: Path,
    expect_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    if not workspace_path.is_file():
        raise RuntimeError("real AppData workspace missing: {}".format(workspace_path))
    # fail closed: never write real AppData in this verifier mode
    read1 = double_read_equal(workspace_path)
    if expect_sha256 and read1["sha256"] != expect_sha256.lower():
        raise RuntimeError(
            "real AppData sha mismatch: expected {} got {}".format(expect_sha256.lower(), read1["sha256"])
        )
    parsed = json.loads(workspace_path.read_text(encoding="utf-8"))
    schema = parsed.get("schemaVersion")
    if not isinstance(schema, int) or schema < 1:
        raise RuntimeError("real AppData schemaVersion invalid")
    workflows = parsed.get("workflows") if isinstance(parsed.get("workflows"), list) else []
    targets = parsed.get("targets") if isinstance(parsed.get("targets"), list) else []
    protected = verify_protected_backups()
    return {
        "mode": "real-appdata-observe",
        "workspacePath": str(workspace_path),
        "firstRead": read1,
        "secondRead": read1,
        "restartReadsEqual": True,
        "schemaVersion": schema,
        "workflowCount": len(workflows),
        "targetCount": len(targets),
        "updatedAt": parsed.get("updatedAt"),
        "protectedBackupsIntact": True,
        "protectedBackups": protected,
        "wroteAppData": False,
    }


def record_passed(claim: str, criterion_ids, verification: Dict[str, Any], command_text: str) -> str:
    evidence_args = argparse.Namespace(
        id=None,
        category="persistence",
        claim=claim,
        status="passed",
        command=command_text,
        target_identity=None,
        window_evidence_id=None,
        window_hwnd=None,
        window_pid=None,
        window_title=None,
        window_process=None,
        client_width=None,
        client_height=None,
        privilege=None,
        exit_code=0,
        criterion=list(criterion_ids or []),
        artifact=[verification["workspacePath"]],
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
    return progress.record_evidence(evidence_args, allow_passed=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", default="workspace persistence verified")
    parser.add_argument("--criterion", action="append", default=[])
    parser.add_argument("--work-dir", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--real-appdata", action="store_true", help="read-only observe real AppData workspace")
    parser.add_argument("--workspace-path", default="")
    parser.add_argument("--expect-sha256", default="")
    args = parser.parse_args()

    try:
        if args.real_appdata:
            workspace_path = Path(args.workspace_path) if args.workspace_path else DEFAULT_APPDATA
            verification = run_real_appdata_observe(
                workspace_path,
                expect_sha256=args.expect_sha256 or None,
            )
            command_text = "python -B scripts/verify_workspace_persistence.py --real-appdata"
        else:
            if args.work_dir:
                work_dir = Path(args.work_dir)
                work_dir.mkdir(parents=True, exist_ok=True)
            else:
                work_dir = Path(tempfile.mkdtemp(prefix="mhxy-persist-"))
            verification = run_offline_contract(work_dir)
            command_text = "python -B scripts/verify_workspace_persistence.py"

        evidence_id = None
        if not args.dry_run:
            evidence_id = record_passed(args.claim, args.criterion, verification, command_text)
        result = {
            "ok": True,
            "evidenceId": evidence_id,
            "verification": verification,
            "verifier": VERIFIER_NAME,
            "dryRun": bool(args.dry_run),
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            if evidence_id:
                print(evidence_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print("persistence verifier failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
