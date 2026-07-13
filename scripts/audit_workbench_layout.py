#!/usr/bin/env python3
"""Audit the P2 workbench layout and inspector accessibility contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def require(failures: list[str], source: str, token: str, message: str) -> None:
    if token not in source:
        failures.append(message)


def audit(root: Path) -> dict[str, object]:
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "src/styles.css").read_text(encoding="utf-8")
    main = (root / "src/main.js").read_text(encoding="utf-8")
    core = (root / "src/workbench-layout-core.js").read_text(encoding="utf-8")
    tests = (root / "scripts/test_workbench_layout_core.mjs").read_text(encoding="utf-8")
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    for token, message in [
        ('id="workspace"', "workspace landmark is missing"),
        ('class="target-rail"', "target rail is missing"),
        ('class="library-panel panel"', "workflow library panel is missing"),
        ('class="step-panel panel"', "step panel is missing"),
        ('class="inspector-panel panel"', "inspector panel is missing"),
        ('class="run-panel panel"', "run panel is missing"),
    ]:
        require(failures, html, token, message)

    for tab in ["workflow", "step", "target"]:
        require(failures, html, f'data-inspector-tab="{tab}"', f"inspector {tab} tab is missing")
        require(failures, html, f'aria-controls="inspector-panel-{tab}"', f"inspector {tab} tab has no aria-controls")
        require(failures, html, f'data-inspector-panel="{tab}"', f"inspector {tab} panel is missing")
        require(failures, html, f'aria-labelledby="inspector-tab-{tab}"', f"inspector {tab} panel has no label")
    if html.count('role="tab"') != 3 or html.count('role="tabpanel"') != 3:
        failures.append("inspector must expose exactly three tabs and three tab panels")

    for token, message in [
        ("grid-template-rows: auto auto auto auto minmax(96px, 1fr);", "step list must own an explicit fifth flexible grid row"),
        ("grid-template-rows: auto auto minmax(0, auto) minmax(96px, 1fr) auto;", "workflow list must keep an explicit non-zero flexible row"),
        (".workflow-list,\n.step-list {\n  min-height: 96px;", "workflow and step lists need a 96px minimum height"),
        ("@media (min-width: 1121px) and (max-height: 900px)", "compact desktop height policy is missing"),
        ("@media (max-width: 1120px)", "stacked layout breakpoint is missing"),
        ("overflow-y: auto;", "stacked layout must restore page scrolling"),
        ("grid-template-columns: minmax(0, 1fr);", "stacked layout must use shrinkable single-column tracks"),
    ]:
        require(failures, css, token, message)

    for token, message in [
        ("workbenchViewportContract", "main must apply the tested viewport contract"),
        ("bindInspectorTabs", "inspector tab keyboard/click binding is missing"),
        ("inspectorTabForFocusSelector", "focus navigation must reveal the owning inspector tab"),
        ('window.addEventListener("resize"', "viewport contract must refresh on resize"),
    ]:
        require(failures, main, token, message)

    for viewport in ["1460, height: 880", "1280, height: 720", "1120, height: 720", "920, height: 680", "820, height: 720"]:
        require(failures, core, viewport, f"required viewport contract is missing: {viewport}")
    for test_name in [
        "testInspectorTabNormalization",
        "testFocusSelectorsChooseReachableInspectorTabs",
        "testRequiredViewportsHaveExplicitLayoutContracts",
    ]:
        require(failures, tests, test_name, f"layout regression test is missing: {test_name}")

    html_ids = set(re.findall(r'\bid="([^"]+)"', html))
    direct_ids = set(re.findall(r'\$\("#([^"]+)"\)', main))
    missing_ids = sorted(direct_ids - html_ids)
    if missing_ids:
        failures.append("main.js references ids missing from index.html: " + ", ".join(missing_ids))

    scripts = package.get("scripts", {})
    if scripts.get("test:workbench-layout") != "node scripts/test_workbench_layout_core.mjs":
        failures.append("package.json must expose test:workbench-layout")
    if scripts.get("audit:workbench-layout") != "python scripts/audit_workbench_layout.py":
        failures.append("package.json must expose audit:workbench-layout")
    if "npm run test:workbench-layout" not in scripts.get("test:all-core", ""):
        failures.append("test:all-core must include test:workbench-layout")
    if "npm run audit:workbench-layout" not in scripts.get("audit:all", ""):
        failures.append("audit:all must include audit:workbench-layout")

    return {
        "passed": not failures,
        "failures": failures,
        "counts": {
            "htmlIds": len(html_ids),
            "directMainIdReferences": len(direct_ids),
            "inspectorTabs": html.count('role="tab"'),
            "requiredViewports": 5,
        },
    }


def main() -> int:
    args = parse_args()
    result = audit(args.project_root.resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result["counts"].items():
            print(f"{key}={value}")
        for failure in result["failures"]:
            print(f"FAIL {failure}")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
