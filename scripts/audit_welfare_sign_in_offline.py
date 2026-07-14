from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    core = (ROOT / "src" / "welfare-sign-in-core.js").read_text(encoding="utf-8")
    main_js = (ROOT / "src" / "main.js").read_text(encoding="utf-8")
    failures = []
    for needle in [
        "WELFARE_SIGNIN_BLUEPRINT",
        "assessWelfareSignInReadiness",
        "button.welfare",
        "button.sign_in",
        "requiresManualConfirmation",
    ]:
        if needle not in core:
            failures.append("missing " + needle)
    if "steps:" not in core and "steps :" not in core:
        failures.append("blueprint steps missing")
    # count step objects roughly
    step_count = core.count("{ type:")
    if step_count < 10:
        failures.append("expected >=10 steps, found " + str(step_count))
    if "welfare-sign-in-core.js" not in main_js:
        failures.append("main.js does not import welfare-sign-in-core")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("audit_welfare_sign_in_offline: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
