"""Runner — Company Metadata Routing Acceptance."""

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
os.environ.setdefault("ASK_TEST_MODE", "inprocess")

from ask_product_test.company_metadata_routing_acceptance_v1 import run  # noqa: E402
from ask_product_test.harness import write_artifact  # noqa: E402


def main() -> int:
    report = run(include_pipeline=os.environ.get("SKIP_PIPELINE") != "1")

    print(f"[company_metadata_routing] version={report['version']} n={report['total']}")
    for r in report["results"]:
        if not r["passed"]:
            print(f"  [FAIL] ({r['kind']}) {r['question']} — {r['failed']}")

    print(
        f"\n[company_metadata_routing] {report['passed']}/{report['total']} "
        f"({report['pass_rate_pct']}%) decision={report['decision']}"
    )
    for kind, bucket in sorted(report["by_kind"].items()):
        print(f"  {kind}: {bucket['passed']}/{bucket['total']}")

    write_artifact("company_metadata_routing_acceptance_v1.json", report)

    if report.get("decision") == "NOT_EVALUATED":
        print(
            f"\n[company_metadata_routing] NOT EVALUATED — {report.get('reason', 'acceptance dataset unavailable')}",
            flush=True,
        )
        return 2

    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
