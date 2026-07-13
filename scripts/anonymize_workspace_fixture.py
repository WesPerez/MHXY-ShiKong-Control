#!/usr/bin/env python3
"""Generate a deterministic, content-free schema v6 migration fixture."""

from __future__ import print_function

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


EXPECTED = {"schemaVersion": 6, "workflows": 5, "steps": 63, "targets": 27}
FIXED_TIME = "2024-01-01T00:00:00.000Z"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def counts(value: Dict[str, Any]) -> Dict[str, int]:
    workflows = value.get("workflows") if isinstance(value.get("workflows"), list) else []
    targets = value.get("targets") if isinstance(value.get("targets"), list) else []
    return {
        "schemaVersion": value.get("schemaVersion"),
        "workflows": len(workflows),
        "steps": sum(len(item.get("steps", [])) for item in workflows if isinstance(item, dict)),
        "targets": len(targets),
    }


def anonymize(source: Dict[str, Any], source_hash: str) -> Dict[str, Any]:
    workflows = source.get("workflows", [])
    targets = source.get("targets", [])
    workflow_ids = {str(item.get("id")): "workflow-{:03d}".format(index) for index, item in enumerate(workflows, 1)}
    step_ids = {
        str(step.get("id")): "step-{:03d}".format(index)
        for index, step in enumerate((step for workflow in workflows for step in workflow.get("steps", [])), 1)
    }
    target_ids = {str(item.get("id")): "target-{:03d}".format(index) for index, item in enumerate(targets, 1)}

    def mapped_target(value: Any, step_type: str) -> str:
        text = str(value or "")
        if text in target_ids:
            return target_ids[text]
        return {
            "hotkey": "ALT+1",
            "delay": "500ms",
            "condition": "last.status",
            "retry_until": "last.status",
            "snapshot": "window.client",
            "restore": "restore.home",
            "text_input": "sample-text",
            "loop": "control.loop",
            "task_jump": "workflow.next",
        }.get(step_type, "target.placeholder")

    anonymized_workflows = []
    for workflow_index, workflow in enumerate(workflows, 1):
        steps = []
        for step_index, step in enumerate(workflow.get("steps", []), 1):
            step_type = str(step.get("type") or "detect_page")
            item = {
                "id": step_ids[str(step.get("id"))],
                "type": step_type,
                "name": "Step {:02d}".format(step_index),
                "target": mapped_target(step.get("target"), step_type),
                "command": {
                    "hotkey": "mode=hwnd-key",
                    "delay": "reason=fixture",
                    "condition": "guard=true",
                    "retry_until": "interval=500ms",
                    "snapshot": "dry-run log only",
                    "restore": "safe sequence",
                }.get(step_type, "mode=fixture"),
                "expect": "fixture.expected",
                "timeoutMs": int(step.get("timeoutMs") or 0),
                "retry": int(step.get("retry") or 0),
                "onFail": str(step.get("onFail") or "stop"),
                "enabled": step.get("enabled") is not False,
                "targetId": target_ids.get(str(step.get("targetId") or step.get("assetId") or ""), ""),
                "notes": "",
            }
            for field in ("targetStepId", "elseTargetStepId", "recoveryStepId"):
                if step.get(field):
                    item[field] = step_ids[str(step[field])]
            if step.get("jumpWorkflowId"):
                item["jumpWorkflowId"] = workflow_ids[str(step["jumpWorkflowId"])]
            if step.get("maxIterations") is not None:
                item["maxIterations"] = int(step.get("maxIterations") or 0)
            steps.append(item)
        anonymized_workflows.append({
            "schemaVersion": 6,
            "id": workflow_ids[str(workflow.get("id"))],
            "name": "Workflow {:02d}".format(workflow_index),
            "category": "Category {:02d}".format(workflow_index),
            "description": "",
            "tags": ["fixture"],
            "initialCheck": target_ids.get(str(workflow.get("initialCheck") or ""), "target-001"),
            "targetPolicy": {
                "titleNeedle": "ANONYMIZED-GAME-WINDOW",
                "inputMode": str(workflow.get("targetPolicy", {}).get("inputMode") or "hwnd-message"),
                "concurrency": str(workflow.get("targetPolicy", {}).get("concurrency") or "per-window-exclusive"),
            },
            "steps": steps,
            "createdAt": FIXED_TIME,
            "updatedAt": FIXED_TIME,
        })

    anonymized_targets = []
    for index, target in enumerate(targets, 1):
        anonymized_targets.append({
            "id": target_ids[str(target.get("id"))],
            "name": "Target {:02d}".format(index),
            "kind": str(target.get("kind") or "unknown"),
            "createdAt": FIXED_TIME,
            "updatedAt": FIXED_TIME,
            "dataUrl": "",
            "roi": None,
            "match": {
                "threshold": float(target.get("match", {}).get("threshold") or 0.86),
                "scope": str(target.get("match", {}).get("scope") or "window"),
            },
            "texts": ["sample-text-{:02d}".format(index)] if target.get("texts") else [],
            "click": {
                "button": str(target.get("click", {}).get("button") or "left"),
                "point": str(target.get("click", {}).get("point") or "center"),
            },
            "source": None,
            "width": 0,
            "height": 0,
            "note": "",
        })

    return {
        "schemaVersion": 6,
        "activeWorkflowId": workflow_ids.get(str(source.get("activeWorkflowId")), anonymized_workflows[0]["id"]),
        "workflows": anonymized_workflows,
        "assignments": {},
        "targets": anonymized_targets,
        "runHistory": [],
        "createdAt": FIXED_TIME,
        "updatedAt": FIXED_TIME,
        "fixtureMetadata": {
            "kind": "mhxy-anonymized-workspace-v6",
            "sourceSha256": source_hash,
            "contentRemoved": ["names", "descriptions", "notes", "paths", "window identities", "image data URLs", "OCR text"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the anonymized v6 migration fixture")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    args = parser.parse_args()
    source_path = Path(args.source).expanduser().resolve(strict=True)
    output_path = Path(args.output).expanduser().resolve(strict=False)
    source_hash = file_sha256(source_path)
    if source_hash != args.expected_source_sha256.upper():
        raise RuntimeError("source hash differs from the verified backup evidence")
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if counts(source) != EXPECTED:
        raise RuntimeError("source does not match the expected schema v6 5/63/27 baseline")
    fixture = anonymize(source, source_hash)
    if counts(fixture) != EXPECTED:
        raise RuntimeError("anonymized fixture changed the required schema/count baseline")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "sha256": file_sha256(output_path), "counts": counts(fixture)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
