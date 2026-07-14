#!/usr/bin/env python3
"""Offline tests for bounded live input verifier helpers and binary build."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_bounded_live_input as verifier  # noqa: E402


def test_parse_roi_and_manual_confirmation() -> None:
    assert verifier.parse_roi("1,2,3,4") == (1, 2, 3, 4)
    try:
        verifier.parse_roi("1,2,0,4")
        raise AssertionError("expected invalid roi")
    except RuntimeError:
        pass
    conf = verifier.parse_manual_confirmation(
        json.dumps(
            {
                "version": 1,
                "targetId": "entry.home",
                "bindingFingerprint": "manual-binding-v1:abc",
                "approvedAt": "2026-07-14T00:00:00Z",
            }
        )
    )
    assert conf["targetId"] == "entry.home"
    assert conf["bindingFingerprint"].startswith("manual-binding-v1:")


def test_validate_step_report_match_only() -> None:
    window_record = {
        "targetIdentity": "game-client:1@MyGame_x64r.exe:2",
        "windowIdentity": {
            "hwnd": 2,
            "pid": 1,
            "title": "梦幻西游：时空",
            "process": "MyGame_x64r.exe",
            "clientWidth": 800,
            "clientHeight": 600,
            "privilege": "elevated",
        },
    }
    report = {
        "kind": "mhxy-shikong.bounded-live-step",
        "version": 1,
        "mode": "match_only",
        "allowInput": False,
        "inputSent": False,
        "matched": True,
        "privilege": "elevated",
        "target": {
            "hwnd": 2,
            "pid": 1,
            "title": "梦幻西游：时空",
            "processName": "MyGame_x64r.exe",
            "clientWidth": 800,
            "clientHeight": 600,
        },
        "foregroundUnchanged": True,
        "cursorUnchanged": True,
    }
    summary = verifier.validate_step_report(
        report,
        "match_only",
        window_record,
        allow_input=False,
        require_postcondition=False,
        min_delta=0.001,
    )
    assert summary["inputSent"] is False
    assert summary["matched"] is True


def test_build_bounded_live_step_binary() -> None:
    # Building is validated separately in CI/manual rebind to avoid nested cargo lock hangs.
    source = ROOT / "src-tauri" / "src" / "bin" / "bounded_live_step.rs"
    assert source.is_file(), "bounded_live_step.rs missing"
    assert "BOUNDED_LIVE_STEP_JSON=" in source.read_text(encoding="utf-8")
    assert "post_hotkey" in source.read_text(encoding="utf-8")
    assert "post_mouse_click" in source.read_text(encoding="utf-8")


def main() -> int:
    test_parse_roi_and_manual_confirmation()
    test_validate_step_report_match_only()
    test_build_bounded_live_step_binary()
    print("test_verify_bounded_live_input: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
