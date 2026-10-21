"""Runner — AGI Core Platform Acceptance Test v1.0 (highest release gate).

Writes artifacts/core_platform_acceptance_v1.{json,md,html}.
Exit 0 only when the suite scores >=98% with zero defects.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ASK_TEST_MODE", "inprocess")
os.environ.setdefault("ASK_TEST_CASE_COOLDOWN_SEC", "0")
os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))
os.environ.setdefault("VALUATION_CONSENSUS_ROOT", str(ROOT / "data" / "valuation_consensus"))

from ask_product_test.core_platform_acceptance_v1 import run  # noqa: E402
from ask_product_test.harness import write_artifact, _artifacts_dir  # noqa: E402

SECTION_TITLES = {
    "A_company_identity": "A — Company Identity",
    "B_financial": "B — Financial Intelligence",
    "C_business": "C — Business Intelligence",
    "D_industry": "D — Industry Intelligence",
    "E_investment": "E — Investment Intelligence",
    "F_research": "F — Research Intelligence",
    "G_consensus": "G — Consensus Intelligence",
    "H_knowledge_unification": "H — Knowledge Unification",
    "I_metadata": "I — Metadata",
    "J_impossible": "J — Impossible Questions",
}

DEFECTS = (
    ("hallucinations", "Hallucinations"),
    ("recommendation_leakage", "Recommendation leakage"),
    ("wrong_entity", "Wrong entity"),
    ("wrong_sector", "Wrong sector"),
    ("metadata_errors", "Metadata errors"),
    ("cross_industry_leakage", "Cross-industry leakage"),
    ("cross_engine_leakage", "Cross-engine leakage"),
)


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AGI Core Platform Acceptance v1.0",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Overall: **{report['overall_score']}%** ({report['passed']}/{report['total']})",
        f"- Target: {report['target_pct']}%",
        f"- Decision: **{report['decision']}**",
        "",
        "## Section scores",
        "",
        "| Section | Pass rate |",
        "|---|---|",
    ]
    for key, pct in report["section_scores"].items():
        lines.append(f"| {SECTION_TITLES.get(key, key)} | {pct}% |")
    lines += ["", "## Zero-defect gates", "", "| Gate | Count |", "|---|---|"]
    for key, label in DEFECTS:
        lines.append(f"| {label} | {report[key]} |")
    latency = report["latency"]
    lines += [
        "",
        "## Latency",
        "",
        "| Metric | Observed | Target |",
        "|---|---|---|",
        f"| P50 | {latency['p50_ms']} ms | {latency['p50_target_ms']} ms |",
        f"| P95 | {latency['p95_ms']} ms | {latency['p95_target_ms']} ms |",
        f"| Average | {latency['avg_ms']} ms | {latency['avg_target_ms']} ms |",
        "",
        "## Accuracy",
        "",
        "| Dimension | Score |",
        "|---|---|",
        f"| Routing | {report['routing_accuracy']}% |",
        f"| Entity | {report['entity_accuracy']}% |",
        f"| Metadata | {report['metadata_accuracy']}% |",
        f"| Financial | {report['financial_accuracy']}% |",
        f"| Business | {report['business_accuracy']}% |",
        f"| Industry | {report['industry_accuracy']}% |",
        f"| Investment | {report['investment_accuracy']}% |",
        f"| Research | {report['research_accuracy']}% |",
        f"| Consensus | {report['consensus_accuracy']}% |",
        f"| Planner / KUL | {report['planner_accuracy']}% |",
    ]
    failures = [r for r in report["results"] if not r["passed"]]
    if failures:
        lines += ["", "## Failures", "", "| ID | Section | Question | Reasons |", "|---|---|---|---|"]
        for r in failures[:80]:
            lines.append(
                f"| {r['id']} | {r['section']} | {r['question'][:70]} | {', '.join(r['failed'])} |"
            )
    return "\n".join(lines) + "\n"


def _html(report: dict[str, Any]) -> str:
    colour = "#1f7a4d" if report["decision"] == "PASS" else "#b42318"
    rows = "".join(
        f"<tr><td>{escape(SECTION_TITLES.get(k, k))}</td><td>{v}%</td></tr>"
        for k, v in report["section_scores"].items()
    )
    defects = "".join(
        f"<tr><td>{escape(label)}</td><td>{report[key]}</td></tr>" for key, label in DEFECTS
    )
    failures = "".join(
        f"<tr><td>{escape(r['id'])}</td><td>{escape(r['section'])}</td>"
        f"<td>{escape(r['question'][:80])}</td><td>{escape(', '.join(r['failed']))}</td></tr>"
        for r in report["results"]
        if not r["passed"]
    )
    latency = report["latency"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AGI Core Platform Acceptance v1.0</title>
<style>
 body {{ font-family: 'IBM Plex Sans', system-ui, sans-serif; margin: 2rem; color: #142033; }}
 h1 {{ margin-bottom: .25rem; }}
 .score {{ font-size: 2.5rem; font-weight: 700; color: {colour}; }}
 table {{ border-collapse: collapse; margin: 1rem 0; min-width: 420px; }}
 th, td {{ border: 1px solid #d7dee8; padding: .45rem .7rem; text-align: left; font-size: .9rem; }}
 th {{ background: #f3f6fa; }}
 .muted {{ color: #5b6b7c; font-size: .85rem; }}
</style></head><body>
<h1>AGI Core Platform Acceptance v1.0</h1>
<p class="muted">Generated {escape(report['generated_at'])}</p>
<p class="score">{report['overall_score']}% — {escape(report['decision'])}</p>
<p class="muted">{report['passed']}/{report['total']} questions, target {report['target_pct']}%</p>
<h2>Section scores</h2><table><tr><th>Section</th><th>Pass rate</th></tr>{rows}</table>
<h2>Zero-defect gates</h2><table><tr><th>Gate</th><th>Count</th></tr>{defects}</table>
<h2>Latency</h2><table>
 <tr><th>Metric</th><th>Observed</th><th>Target</th></tr>
 <tr><td>P50</td><td>{latency['p50_ms']} ms</td><td>{latency['p50_target_ms']} ms</td></tr>
 <tr><td>P95</td><td>{latency['p95_ms']} ms</td><td>{latency['p95_target_ms']} ms</td></tr>
 <tr><td>Average</td><td>{latency['avg_ms']} ms</td><td>{latency['avg_target_ms']} ms</td></tr>
</table>
{'<h2>Failures</h2><table><tr><th>ID</th><th>Section</th><th>Question</th><th>Reasons</th></tr>' + failures + '</table>' if failures else '<p><strong>No failures.</strong></p>'}
</body></html>
"""


def main() -> int:
    limit = int(os.environ.get("CPA_LIMIT") or "0") or None
    print("[core_platform_acceptance] running AGI Core Platform Acceptance v1.0", flush=True)
    report = run(limit=limit)
    report["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    print(f"\n[core_platform_acceptance] version={report['version']} n={report['total']}")
    for key, pct in report["section_scores"].items():
        bucket = report["sections"][key]
        print(f"  {SECTION_TITLES.get(key, key):34s} {bucket['passed']:3d}/{bucket['total']:<3d} ({pct}%)")
    print("\n  zero-defect gates:")
    for key, label in DEFECTS:
        print(f"    {label:26s} {report[key]}")
    latency = report["latency"]
    print(
        f"\n  latency p50={latency['p50_ms']}ms p95={latency['p95_ms']}ms "
        f"avg={latency['avg_ms']}ms within_budget={latency['within_budget']}"
    )
    failures = [r for r in report["results"] if not r["passed"]]
    if failures:
        print(f"\n  failures ({len(failures)}):")
        for r in failures[:40]:
            print(f"    [FAIL] {r['id']} ({r['section']}) {r['question'][:60]} — {r['failed']}")
    print(
        f"\n[core_platform_acceptance] {report['passed']}/{report['total']} "
        f"({report['overall_score']}%) decision={report['decision']}"
    )

    art_dir = _artifacts_dir()
    write_artifact("core_platform_acceptance_v1.json", report)
    (art_dir / "core_platform_acceptance_v1.md").write_text(_markdown(report), encoding="utf-8")
    (art_dir / "core_platform_acceptance_v1.html").write_text(_html(report), encoding="utf-8")

    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
