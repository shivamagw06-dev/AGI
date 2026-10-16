"""Runner — Canonical Company Classification Acceptance (300 questions)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))
os.environ.setdefault("VALUATION_CONSENSUS_ROOT", str(ROOT / "data" / "valuation_consensus"))

from ask_product_test.canonical_classification_acceptance_v1 import run  # noqa: E402
from ask_product_test.harness import write_artifact  # noqa: E402


def main() -> int:
    target = int(os.environ.get("CCA_TARGET_QUESTIONS", "300"))
    report = run(target_questions=target)

    print(f"[canonical_classification] version={report['version']} n={report['total']}")
    for r in report["results"]:
        if not r["passed"]:
            print(f"  [FAIL] {r['id']} {r['ticker']} — {r['failed']} {r['leak_violations']}")

    if report.get("decision") == "NOT_EVALUATED":
        print(
            f"\n[canonical_classification] NOT EVALUATED — {report.get('reason', 'acceptance dataset unavailable')}",
            flush=True,
        )
        write_artifact("canonical_classification_acceptance_v1.json", report)
        return 2

    print(
        f"\n[canonical_classification] {report['passed']}/{report['total']} "
        f"({report['pass_rate_pct']}%) decision={report['decision']}"
    )
    print(
        f"  golden: {report['golden_passed']}/{report['golden_total']} "
        f"({report['golden_pass_rate_pct']}%)"
    )
    print(f"  sectors covered: {report['sectors_covered_count']}/11")
    print(f"  cross-industry leakage: {report['cross_industry_leakage']}")
    print(f"  wrong sector: {report['wrong_sector']}  wrong industry: {report['wrong_industry']}")

    write_artifact("canonical_classification_acceptance_v1.json", report)

    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
