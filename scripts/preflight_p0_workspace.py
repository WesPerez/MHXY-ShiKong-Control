#!/usr/bin/env python3
"""Read-only P0 workspace identity and migration-baseline preflight."""

from __future__ import print_function

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


EXPECTED = {"schemaVersion": 6, "workflows": 5, "steps": 63, "targets": 27}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def inspect(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "readOnlyOperation": True,
    }
    if not path.is_file():
        result["errors"] = ["file_missing"]
        return result
    raw = path.read_bytes()
    result.update(
        {
            "size": len(raw),
            "modifiedAtUtc": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
    )
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        result["errors"] = ["invalid_json: {}".format(exc)]
        return result
    if not isinstance(value, dict):
        result["errors"] = ["root_not_object"]
        return result
    workflows = value.get("workflows") if isinstance(value.get("workflows"), list) else []
    targets = value.get("targets") if isinstance(value.get("targets"), list) else []
    assignments_value = value.get("assignments")
    if isinstance(assignments_value, (list, dict)):
        assignments_count = len(assignments_value)
    else:
        assignments_count = 0
    run_history = value.get("runHistory") if isinstance(value.get("runHistory"), list) else []
    steps = 0
    for workflow in workflows:
        if isinstance(workflow, dict) and isinstance(workflow.get("steps"), list):
            steps += len(workflow["steps"])
    result.update(
        {
            "schemaVersion": value.get("schemaVersion"),
            "counts": {
                "workflows": len(workflows),
                "steps": steps,
                "targets": len(targets),
                "assignments": assignments_count,
                "runHistory": len(run_history),
            },
        }
    )
    checks = {
        "schemaVersion": value.get("schemaVersion") == EXPECTED["schemaVersion"],
        "workflows": len(workflows) == EXPECTED["workflows"],
        "steps": steps == EXPECTED["steps"],
        "targets": len(targets) == EXPECTED["targets"],
    }
    result["checks"] = checks
    result["baselineMatches"] = all(checks.values())
    result["errors"] = [] if result["baselineMatches"] else [key + "_mismatch" for key, passed in checks.items() if not passed]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only identity check for the real schema v6 workspace and its existing backup")
    parser.add_argument("--app-data-dir", help="Override the Tauri AppData directory for a fixture or test")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if args.app_data_dir:
        app_data_dir = Path(args.app_data_dir).expanduser().resolve()
    else:
        roaming = os.environ.get("APPDATA")
        if not roaming:
            print("APPDATA is not available", file=sys.stderr)
            return 2
        app_data_dir = Path(roaming) / "local.mhxy.shikong.control"

    files: List[Dict[str, Any]] = [
        inspect(app_data_dir / "workspace.json"),
        inspect(app_data_dir / "workspace.json.bak"),
    ]
    output = {
        "kind": "mhxy-shikong.p0-workspace-preflight",
        "schemaVersion": 1,
        "capturedAtUtc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "readOnly": True,
        "appDataDirectory": str(app_data_dir),
        "expectedBaseline": EXPECTED,
        "files": files,
        "readyForNonOverwritingBackupIntent": all(item.get("baselineMatches") for item in files),
        "nextAction": "Choose two new destination names, prove they do not exist, then register appdata_backup action intent before copying.",
        "prohibitedActions": [
            "Do not launch the current HEAD application before independent backups exist.",
            "Do not overwrite workspace.json or workspace.json.bak.",
            "Do not send game input or stop preexisting processes during P0 preflight.",
        ],
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for item in files:
            print("{}: exists={} schema={} workflows={} steps={} targets={} size={} sha256={} modifiedAtUtc={}".format(
                item.get("path"),
                item.get("exists"),
                item.get("schemaVersion"),
                item.get("counts", {}).get("workflows"),
                item.get("counts", {}).get("steps"),
                item.get("counts", {}).get("targets"),
                item.get("size"),
                item.get("sha256"),
                item.get("modifiedAtUtc"),
            ))
        print("readyForNonOverwritingBackupIntent={}".format(output["readyForNonOverwritingBackupIntent"]))
    return 0 if output["readyForNonOverwritingBackupIntent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
