#!/usr/bin/env python3
"""Audit the P1 per-HWND runtime lane and frontend execution contract."""

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


def function_block(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    following = source[start + len(signature) :]
    next_function = re.search(r"\n(?:pub\s+)?fn\s+", following)
    end = start + len(signature) + next_function.start() if next_function else len(source)
    return source[start:end]


def audit(project_root: Path) -> dict[str, object]:
    rust_main = (project_root / "src-tauri/src/main.rs").read_text(encoding="utf-8")
    lane = (project_root / "src-tauri/src/runtime/window_lane.rs").read_text(encoding="utf-8")
    ocr_pool = (project_root / "src-tauri/src/runtime/ocr_pool.rs").read_text(encoding="utf-8")
    vision_path = project_root / "src-tauri/src/runtime/vision_match.rs"
    vision_match = vision_path.read_text(encoding="utf-8") if vision_path.is_file() else ""
    frontend = (project_root / "src/main.js").read_text(encoding="utf-8")
    package = json.loads((project_root / "package.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    if not vision_match:
        failures.append("budgeted template matching module is missing")

    for field in ["session_id", "step_id", "deadline_ms", "cancel_token_id"]:
        require(failures, lane, f"pub {field}:", f"execution context is missing {field}")
    for token, message in [
        ("pub struct WindowLaneRegistry", "WindowLaneRegistry is missing"),
        ("queue: VecDeque<u64>", "per-HWND FIFO queue is missing"),
        ("active_sessions: HashMap<SessionKey, Arc<Mutex<()>>>", "per-session input commit gates are missing"),
        ("cancelled_sessions: HashSet<SessionKey>", "token-scoped cancellation tracking is missing"),
        ("pub struct ExecutionControl", "ExecutionControl is missing"),
        ("pub fn commit_input", "linearized input commit gate is missing"),
        ("pub fn acquire(", "lane acquire entry is missing"),
        ("pub fn cancel_session(", "lane cancellation entry is missing"),
        ("pub fn complete_session(", "lane completion cleanup is missing"),
        ("completed_session_releases_cancellation_state_and_rejects_late_cancel", "session cleanup regression test is missing"),
        ("cancelled_before_input_commit_never_calls_the_action", "cancel-before-input zero-call test is missing"),
        ("deadline_before_input_commit_never_calls_the_action", "deadline-before-input zero-call test is missing"),
        ("input_commit_and_cancel_are_linearized_per_session", "input/cancel linearization test is missing"),
        ("different_sessions_can_commit_input_concurrently", "per-session commit gates must preserve cross-session concurrency"),
    ]:
        require(failures, lane, token, message)

    command_start = rust_main.find("async fn execute_workflow_step(")
    unlocked_start = rust_main.find("fn execute_workflow_step_unlocked(")
    if command_start < 0 or unlocked_start <= command_start:
        failures.append("execute_workflow_step must be an async command with an unlocked helper")
        command = ""
    else:
        command = rust_main[command_start:unlocked_start]
    require(failures, command, "tauri::async_runtime::spawn_blocking", "workflow execution must leave the Tauri IPC handler before blocking")
    require(failures, command, ".acquire(hwnd, execution)", "the lane permit must be acquired inside the blocking worker")
    require(failures, command, "let control = permit.control()", "the lane permit must create an execution control")
    require(
        failures,
        command,
        "execute_workflow_step_unlocked(hwnd, step, expected_window, &control, &ocr_pool)",
        "dispatch must run with the permit execution control and managed OCR pool",
    )
    if command.find("spawn_blocking") > command.find(".acquire(hwnd, execution)"):
        failures.append("lane acquire must occur inside spawn_blocking")

    for token, message in [
        ("app.manage(WindowLaneRegistry::new())", "Tauri must manage one WindowLaneRegistry"),
        ("cancel_session,", "cancel_session must be registered as a Tauri command"),
        ("complete_session,", "complete_session must be registered as a Tauri command"),
        ("cancel_token_id: String", "cancel commands must receive cancelTokenId"),
    ]:
        require(failures, rust_main, token, message)

    matcher = function_block(vision_match, "pub fn match_template_budgeted(")
    for token, message in [
        ("CHECKPOINT_PIXEL_BUDGET", "template matching must define a bounded checkpoint budget"),
        ("pixels_since_checkpoint", "template matching must track work between checkpoints"),
        ("checkpoint()?", "template matching must execute cancellation/deadline checkpoints"),
    ]:
        require(failures, matcher, token, message)
    require(failures, rust_main, "template_match_stops_on_cancel_checkpoint", "template cancellation test is missing")
    require(failures, rust_main, "template_match_stops_on_deadline_checkpoint", "template deadline test is missing")

    for signature in [
        "fn dispatch_hotkey_step(",
        "fn dispatch_text_input_step(",
        "fn dispatch_click_step(",
        "fn dispatch_image_step(",
    ]:
        block = function_block(rust_main, signature)
        require(failures, block, "control.commit_input", f"{signature} must use the linearized input gate")
    ocr_dispatch = function_block(rust_main, "fn dispatch_ocr_step(")
    if ocr_dispatch.count("control.checkpoint()?") < 2:
        failures.append("OCR dispatch must check execution before and after strict capture")
    require(failures, ocr_dispatch, "ocr_pool.execute(control", "OCR recognition must run through the managed worker pool")
    require(failures, ocr_pool, "control.check_typed()", "OCR pool must check typed cancel/deadline state while waiting")
    require(failures, ocr_pool, "job.control.check_typed()", "OCR workers must check typed state before and after backend work")

    for field in ["sessionId:", "stepId:", "deadlineMs:", "cancelTokenId:"]:
        if frontend.count(field) < 2:
            failures.append(f"frontend execution calls must provide {field[:-1]} for runs and target probes")
    require(failures, frontend, 'invokeBackend("cancel_session"', "frontend stop must call cancel_session")
    require(failures, frontend, 'invokeBackend("complete_session"', "frontend terminal paths must call complete_session")
    require(failures, frontend, "probeCancelTokenId", "target probes must use a unique cancel token")

    scripts = package.get("scripts", {})
    if scripts.get("audit:runtime-lane") != "python scripts/audit_runtime_lane.py":
        failures.append("package.json must expose audit:runtime-lane")
    if "npm run audit:runtime-lane" not in scripts.get("audit:all", ""):
        failures.append("audit:all must include audit:runtime-lane")

    return {
        "passed": not failures,
        "failures": failures,
        "counts": {
            "executionContextFields": 4,
            "frontendExecutionContexts": frontend.count("execution: {"),
            "runtimeTests": lane.count("#[test]"),
            "templateCheckpointTests": vision_match.count("checkpoint_can_cancel_search")
            + rust_main.count("template_match_stops_on_"),
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
