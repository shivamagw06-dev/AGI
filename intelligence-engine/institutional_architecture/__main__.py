"""CI entrypoint: python -m institutional_architecture

Exit 0 when conformance passes; exit 1 on violations (when fail-on-violation).
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="institutional_architecture",
        description="AGIB v1.0 Architecture Conformance (RC-01)",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument("--quiet", action="store_true", help="Only print summary line")
    parser.add_argument("--force", action="store_true", help="Bypass result cache")
    args = parser.parse_args(argv)

    from institutional_architecture.flags import fail_on_violation
    from institutional_architecture.production import run

    result = run({"force": args.force})
    score = (result.get("architecture_score") or {}).get("score")
    grade = (result.get("architecture_score") or {}).get("grade")
    violations = result.get("violation_count") or 0
    ready = result.get("release_candidate_ready")

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif args.quiet:
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"RC-01 {status} score={score} grade={grade} violations={violations}")
    else:
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"RC-01 Architecture Conformance — {status}")
        print(f"  Score: {score} ({grade})")
        print(f"  Violations: {violations}")
        print(f"  Release candidate ready: {ready}")
        for v in (result.get("violations") or [])[:20]:
            print(f"  ✗ [{v.get('section') or v.get('kind')}] {v.get('message') or v}")
        if result.get("ok"):
            print("  ✓ AGIB v1.0 architectural principles preserved")

    if result.get("ok"):
        return 0
    return 1 if fail_on_violation() else 0


if __name__ == "__main__":
    sys.exit(main())
