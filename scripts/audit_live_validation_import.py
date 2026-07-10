#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(failures: list[str], source: str, needle: str, label: str) -> None:
    if needle not in source:
        failures.append(label)


def require_regex(failures: list[str], source: str, pattern: str, label: str) -> None:
    if not re.search(pattern, source, flags=re.S):
        failures.append(label)


def main() -> int:
    failures: list[str] = []
    paths = [
        "src/live-validation-core.js",
        "scripts/test_live_validation_core.mjs",
        "src/main.js",
        "index.html",
        "package.json",
        "README.md",
        "docs/workflow-model.md",
    ]
    for path in paths:
        if not (ROOT / path).is_file():
            failures.append(f"missing {path}")
    if failures:
        return report(failures)

    core = read_text("src/live-validation-core.js")
    test = read_text("scripts/test_live_validation_core.mjs")
    main_js = read_text("src/main.js")
    html = read_text("index.html")
    package = json.loads(read_text("package.json"))
    docs = "\n".join([read_text("README.md"), read_text("docs/workflow-model.md")])

    for needle in [
        "liveValidationRunHistoryEntry",
        "mergeLiveValidationRunHistory",
        "isLiveValidationEvidence",
        "externalEvidence",
        "processSnapshotCount",
        "outputLimit",
        "preflight_only",
        "input_not_allowed",
        "blocked_by_privilege_or_setup",
        "failed",
        "passed",
        "<truncated>",
        'source: "live-validation"',
    ]:
        require(failures, core, needle, f"live validation core missing {needle}")
    require_regex(
        failures,
        core,
        r"processSnapshotCount:\s*processes\.length",
        "live validation core must store process snapshot summary, not raw process snapshot",
    )
    if "processSnapshot:" in core:
        failures.append("live validation runHistory entry must not store raw processSnapshot")

    for needle in [
        "testPreflightBecomesLightweightRunHistory",
        "testRequireExecutedWithoutAllowInputBecomesStoppedFailureReport",
        "testBlockedRunKeepsOnlyClippedOutput",
        "testPassedParallelLiveRunIsDoneAndInputSent",
        "testMergesByEvidenceIdAndTrimsHistory",
        "testRejectsInvalidEvidenceKind",
        "failureEvidenceBundle",
        "<truncated>",
    ]:
        require(failures, test, needle, f"live validation test missing {needle}")

    scripts = package.get("scripts", {})
    if scripts.get("test:live-validation") != "node scripts/test_live_validation_core.mjs":
        failures.append("package.json missing test:live-validation script")
    if scripts.get("audit:live-validation-import") != "python scripts/audit_live_validation_import.py":
        failures.append("package.json missing audit:live-validation-import script")

    for needle in [
        "liveValidationRunHistoryEntry",
        "mergeLiveValidationRunHistory",
        "importLiveValidationReport",
        "isLiveValidationEvidence",
        "live_validation",
        "Live 验收",
        "externalEvidence",
        "markDirty(\"live validation imported\")",
        "saveWorkspaceNow()",
    ]:
        require(failures, main_js, needle, f"main.js missing live import wiring: {needle}")
    require_regex(
        failures,
        main_js,
        r"state\.workspace\.runHistory\s*=\s*mergeLiveValidationRunHistory",
        "main.js must merge live report into runHistory with dedupe/limit",
    )

    require(failures, html, 'id="import-live-report"', "index.html missing import-live-report button")
    for needle in [
        "导入 live 报告",
        "runHistory",
        "不会发送后台输入",
        "externalEvidence",
        "reports/live-background-hotkey",
    ]:
        require(failures, docs, f"{needle}", f"docs missing live import note: {needle}")

    return report(failures)


def report(failures: list[str]) -> int:
    if failures:
        print("live validation import audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("live validation import audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
