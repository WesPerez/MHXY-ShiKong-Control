#!/usr/bin/env python3
"""Verify that P0 backup/fixture work did not cross live safety boundaries."""

from __future__ import print_function

import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
EXECUTION_DIR = ROOT / "docs" / "execution"
ALLOWED_ACTION_KINDS = {"appdata_backup"}
EXPECTED_BACKUP_CRITERIA = {"P0-S1-C1", "P0-S1-C2"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def controller_processes() -> List[Dict[str, str]]:
    if os.name != "nt":
        raise RuntimeError("P0 controller process audit currently requires Windows")
    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq mhxy-shikong-control.exe", "/FO", "CSV", "/NH"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    if completed.returncode != 0:
        raise RuntimeError("tasklist failed: {}".format(completed.stderr.strip()))
    rows = []
    for row in csv.reader(io.StringIO(completed.stdout)):
        if row and row[0].lower() == "mhxy-shikong-control.exe":
            rows.append({"name": row[0], "pid": row[1] if len(row) > 1 else "unknown"})
    return rows


def audit() -> Dict[str, Any]:
    state = load_json(EXECUTION_DIR / "state.json")
    events = load_jsonl(EXECUTION_DIR / "events.jsonl")
    evidence = load_jsonl(EXECUTION_DIR / "evidence.jsonl")
    run_id = state.get("run", {}).get("runId")
    run_events = [event for event in events if event.get("runId") == run_id]
    action_intents = [event.get("details") or {} for event in run_events if event.get("eventType") == "action_intent"]
    forbidden_actions = [action for action in action_intents if action.get("kind") not in ALLOWED_ACTION_KINDS]
    backup_results = [
        event.get("details") or {}
        for event in run_events
        if event.get("eventType") == "action_result" and (event.get("details") or {}).get("kind") == "appdata_backup"
    ]
    backup_evidence = [
        record for record in evidence
        if record.get("runId") == run_id and record.get("category") == "appdata_backup" and record.get("status") == "passed"
    ]
    criteria = {item.get("id"): item for item in state.get("activeSlice", {}).get("acceptanceCriteria", [])}
    controllers = controller_processes()
    failures = []
    if state.get("inFlightAction") or state.get("actionStatus") == "unknown_after_interruption":
        failures.append("an external action remains unresolved")
    if forbidden_actions:
        failures.append("non-backup side-effect actions were recorded during P0")
    if state.get("safety", {}).get("realInputSent"):
        failures.append("state records real game input")
    if controllers:
        failures.append("mhxy-shikong-control.exe is currently running")
    if len(backup_results) != 2 or any(item.get("status") != "succeeded" or not item.get("verifiedEvidenceId") for item in backup_results):
        failures.append("two verifier-backed successful backup results are required")
    if len(backup_evidence) != 2:
        failures.append("two passed appdata_backup evidence records are required")
    if any(criteria.get(item, {}).get("status") != "passed" for item in EXPECTED_BACKUP_CRITERIA):
        failures.append("P0 backup criteria C1/C2 are not both passed")
    if state.get("runtime", {}).get("managedProcesses"):
        failures.append("P0 state unexpectedly contains managed processes")
    return {
        "kind": "mhxy-shikong.p0-safety-boundary-audit",
        "schemaVersion": 1,
        "passed": not failures,
        "failures": failures,
        "runId": run_id,
        "actionKinds": [item.get("kind") for item in action_intents],
        "backupEvidenceIds": [item.get("id") for item in backup_evidence],
        "controllerProcesses": controllers,
        "realInputSent": bool(state.get("safety", {}).get("realInputSent")),
        "managedProcessCount": len(state.get("runtime", {}).get("managedProcesses", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the P0 no-live-side-effect boundary")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["passed"]:
        print("P0 safety boundary audit passed")
    else:
        for failure in result["failures"]:
            print("ERROR: " + failure)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
