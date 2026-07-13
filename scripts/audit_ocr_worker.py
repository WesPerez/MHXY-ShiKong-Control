#!/usr/bin/env python3
"""Audit the bounded OCR worker pool and failure-classification contract."""

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


def read_source(path: Path, failures: list[str], label: str) -> str:
    if not path.is_file():
        failures.append(f"{label} is missing: {path.relative_to(path.parents[2])}")
        return ""
    return path.read_text(encoding="utf-8")


def require(failures: list[str], source: str, token: str, message: str) -> None:
    if token not in source:
        failures.append(message)


def require_pattern(
    failures: list[str], source: str, pattern: str, message: str, *, flags: int = 0
) -> None:
    if re.search(pattern, source, flags) is None:
        failures.append(message)


def rust_function_block(source: str, name_pattern: str) -> str:
    match = re.search(rf"(?:pub\s+)?fn\s+(?:{name_pattern})\s*\(", source)
    if match is None:
        return ""
    opening = source.find("{", match.end())
    if opening < 0:
        return ""
    depth = 0
    for index in range(opening, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    return source[match.start() :]


def audit(project_root: Path) -> dict[str, object]:
    failures: list[str] = []
    pool_path = project_root / "src-tauri/src/runtime/ocr_pool.rs"
    pool = read_source(pool_path, failures, "OCR worker pool")
    runtime_mod = read_source(project_root / "src-tauri/src/runtime/mod.rs", failures, "runtime module")
    rust_main = read_source(project_root / "src-tauri/src/main.rs", failures, "Rust main")
    frontend = read_source(project_root / "src/main.js", failures, "frontend")
    control_flow = read_source(
        project_root / "src/control-flow-core.js", failures, "control-flow core"
    )
    failure_evidence = read_source(
        project_root / "src/failure-evidence-core.js", failures, "failure-evidence core"
    )
    control_flow_tests = read_source(
        project_root / "scripts/test_control_flow_core.mjs", failures, "control-flow tests"
    )
    failure_evidence_tests = read_source(
        project_root / "scripts/test_failure_evidence_core.mjs",
        failures,
        "failure-evidence tests",
    )

    require_pattern(
        failures,
        pool,
        r"const\s+[A-Z0-9_]*WORKER[A-Z0-9_]*\s*:\s*usize\s*=\s*2\s*;",
        "default OCR worker count must be exactly 2",
    )
    require_pattern(
        failures,
        pool,
        r"const\s+[A-Z0-9_]*(?:QUEUE|CAPACITY)[A-Z0-9_]*\s*:\s*usize\s*=\s*8\s*;",
        "default OCR queue capacity must be exactly 8",
    )
    for token, message in [
        ("pub struct OcrWorkerPool", "OcrWorkerPool is missing"),
        ("sync_channel", "OCR jobs must use a bounded sync_channel"),
        ("try_send", "OCR queue saturation must use immediate try_send backpressure"),
        ("QueueFull", "typed OCR QueueFull failure is missing"),
        ("Cancelled", "typed OCR cancellation failure is missing"),
        ("Queued", "typed OCR queued cancellation/deadline stage is missing"),
        ("Running", "typed OCR running cancellation/deadline stage is missing"),
        ("WorkerUnavailable", "typed OCR worker-unavailable failure is missing"),
        ("BackendFailed", "typed OCR backend failure is missing"),
    ]:
        require(failures, pool, token, message)
    if "DeadlineExceeded" not in pool and "TimedOut" not in pool and "Timeout" not in pool:
        failures.append("typed OCR deadline/timeout failure is missing")
    if "loop {" not in pool and "while let" not in pool:
        failures.append("fixed OCR worker receive loop is missing")

    submit = rust_function_block(pool, r"submit|execute|recognize|run")
    if not submit:
        failures.append("OCR worker pool submission method is missing")
    else:
        require(failures, submit, "try_send", "OCR submission must use non-blocking try_send")
        if "thread::spawn" in submit or "Builder::new()" in submit:
            failures.append("OCR submission must not spawn a thread per job")

    require(failures, runtime_mod, "pub mod ocr_pool;", "runtime module must export ocr_pool")
    require(failures, runtime_mod, "OcrWorkerPool", "runtime module must re-export OcrWorkerPool")

    dispatch = rust_function_block(rust_main, "dispatch_ocr_step")
    require(failures, rust_main, "OcrWorkerPool", "Rust main must use OcrWorkerPool")
    require_pattern(
        failures,
        dispatch,
        r"ocr_pool\s*\.\s*(?:submit|execute|recognize|run)\s*\(",
        "OCR dispatch must submit recognition through OcrWorkerPool",
    )
    if re.search(r"let\s+recognized\s*=\s*recognize_ocr_text\s*\(", dispatch):
        failures.append("OCR dispatch must not call recognize_ocr_text directly")

    rust_statuses = ["ocr_queue_full", "timeout", "cancelled", "ocr_unavailable"]
    for status in rust_statuses:
        require(failures, rust_main, f'"{status}"', f"Rust OCR result status is missing: {status}")

    frontend_contract = "\n".join([frontend, control_flow, failure_evidence])
    frontend_tests = "\n".join([control_flow_tests, failure_evidence_tests])
    for status in rust_statuses:
        require(
            failures,
            frontend_contract,
            f'"{status}"',
            f"frontend failure classification is missing: {status}",
        )
        require(
            failures,
            frontend_tests,
            f'"{status}"',
            f"frontend regression coverage is missing: {status}",
        )
    require(
        failures,
        frontend,
        "backgroundFailureStatuses",
        "frontend runner failure status set is missing",
    )

    required_tests = [
        "worker_count_stays_bounded",
        "queue_full_returns_immediately",
        "workers_execute_in_parallel",
        "queued_cancel_never_calls_backend",
        "queued_deadline_never_calls_backend",
        "running_cancel_discards_late_result",
        "running_deadline_discards_late_result",
        "timed_out_worker_slot_is_not_reused_early",
        "backend_panic_keeps_worker_pool_available",
    ]
    for test_name in required_tests:
        require(failures, pool, f"fn {test_name}(", f"OCR pool regression test is missing: {test_name}")

    return {
        "passed": not failures,
        "failures": failures,
        "counts": {
            "poolTests": pool.count("#[test]"),
            "rustStatuses": sum(f'"{status}"' in rust_main for status in rust_statuses),
            "frontendStatuses": sum(
                f'"{status}"' in frontend_contract for status in rust_statuses
            ),
            "requiredTests": len(required_tests),
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
