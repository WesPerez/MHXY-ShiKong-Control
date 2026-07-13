#!/usr/bin/env python3
"""Audit the Playwright workbench viewport verifier without starting a server."""

from __future__ import annotations

import argparse
import json
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
    config = (root / "playwright.workbench.config.mjs").read_text(encoding="utf-8")
    test = (root / "scripts/playwright/workbench-viewports.spec.mjs").read_text(encoding="utf-8")
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    for token in [
        '["desktop-1460x880", 1460, 880]',
        '["desktop-1280x720", 1280, 720]',
        '["stacked-1120x720", 1120, 720]',
        '["stacked-920x680", 920, 680]',
        '["single-820x720", 820, 720]',
    ]:
        require(failures, config, token, f"Playwright project is missing: {token}")
    for token, message in [
        ("127.0.0.1:4173", "preview server must bind a fixed localhost port"),
        ("--strictPort", "preview server must fail instead of taking an unrelated port"),
        ("reuseExistingServer: false", "verifier must not silently reuse an unowned server"),
        ("workers: 1", "viewport runs must remain serialized"),
        ("playwright-workbench/report.json", "JSON report path is missing"),
    ]:
        require(failures, config, token, message)

    for token, message in [
        ("document.documentElement.scrollWidth", "horizontal overflow metric is missing"),
        ("document.documentElement.clientWidth", "viewport client width metric is missing"),
        ('rect("#workflow-list")', "workflow list height metric is missing"),
        ('rect("#step-list")', "step list height metric is missing"),
        ("toBeGreaterThanOrEqual(95)", "list minimum-height assertion is missing"),
        ("scrollIntoViewIfNeeded", "control reachability assertion is missing"),
        ("page.screenshot", "full-page screenshot evidence is missing"),
        ('page.keyboard.press("ArrowRight")', "keyboard tab navigation assertion is missing"),
        ('toHaveAttribute("aria-selected", "true")', "selected tab ARIA assertion is missing"),
        ('#workflow-list .workflow-row', "workflow-driven tab navigation is missing"),
        ('#step-list .step-row', "step-driven tab navigation is missing"),
        ('#target-list .target-row', "target-driven tab navigation is missing"),
    ]:
        require(failures, test, token, message)

    scripts = package.get("scripts", {})
    if scripts.get("test:ui-viewports") != "playwright test -c playwright.workbench.config.mjs":
        failures.append("package.json must expose test:ui-viewports")
    if scripts.get("test:ui-viewports:list") != "playwright test --list -c playwright.workbench.config.mjs":
        failures.append("package.json must expose a server-free Playwright discovery command")
    if scripts.get("audit:workbench-viewports") != "python scripts/audit_workbench_viewport_test.py":
        failures.append("package.json must expose audit:workbench-viewports")
    if "npm run audit:workbench-viewports" not in scripts.get("audit:all", ""):
        failures.append("audit:all must include audit:workbench-viewports")

    dev_dependencies = package.get("devDependencies", {})
    lock_packages = lock.get("packages", {})
    if "@playwright/test" not in dev_dependencies:
        failures.append("@playwright/test is missing from devDependencies")
    if "node_modules/@playwright/test" not in lock_packages:
        failures.append("package-lock.json does not contain @playwright/test")

    return {
        "passed": not failures,
        "failures": failures,
        "counts": {
            "viewportProjects": config.count("x720") + config.count("x880") + config.count("x680"),
            "reachableControls": test.count('"#') - 9,
            "layoutTests": test.count('test("'),
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
