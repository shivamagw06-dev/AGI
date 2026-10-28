"""Runner — AGI Answer Quality Acceptance v1.0 (Phase 4.0).

Writes artifacts/answer_quality_acceptance_v1.{json,md,html}.
Exit 0 only when the suite scores >=95% with every quality gate at zero.
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

from ask_product_test.answer_quality_acceptance_v1 import run  # noqa: E402
from ask_product_test.harness import write_artifact, _artifacts_dir  # noqa: E402

SECTION_TITLES = {
    "A_company": "A — Company Intelligence",
    "B_financial": "B — Financial Intelligence",
    "C_business": "C — Business Intelligence",
    "D_industry": "D — Industry Intelligence",
    "E_investment": "E — Investment Intelligence",
    "F_research": "F — Research Intelligence",
    "G_consensus": "G — Consensus Intelligence",
    "H_fusion": "H — Knowledge Fusion",
    "I_executive": "I — Executive Communication",
    "J_impossible": "J — Impossible Questions",
}

GATE_TITLES = {
    "boilerplate": "Boilerplate clusters",
    "generic_investment_thesis": "Generic investment thesis",
    "generic_research_answer": "Generic research answer",
    "industry_refusal": "Industry refusal",
    "wrong_evidence": "Wrong evidence",
    "hallucination": "Company answered generically",
    "recommendation_leakage": "Recommendation leakage",
    "unexpected_refusal": "Unexpected refusal",
}


def _markdown(r: dict[str, Any]) -> str:
    lines = [
        "# AGI Answer Quality Acceptance v1.0",
        "",
        f"- Generated: {r['generated_at']}",
        f"- Overall: **{r['overall_score']}%** ({r['passed']}/{r['total']})",
        f"- Target: {r['target_pct']}% · case pass score {r['case_pass_score']}",
        f"- Decision: **{r['decision']}**",
        "",
        "## Section quality",
        "",
        "| Section | Pass rate | Avg quality |",
        "|---|---|---|",
    ]
    for key, pct in r["section_scores"].items():
        lines.append(f"| {SECTION_TITLES.get(key, key)} | {pct}% | {r['section_avg_quality'][key]} |")
    lines += ["", "## Quality gates", "", "| Gate | Count |", "|---|---|"]
    for key, count in r["gates"].items():
        lines.append(f"| {GATE_TITLES.get(key, key)} | {count} |")
    lines += ["", "## Dimension averages", "", "| Dimension | Score |", "|---|---|"]
    for dim, val in r["dimension_avg"].items():
        lines.append(f"| {dim.replace('_', ' ')} | {val}% |")
    if r["weak_companies"]:
        lines += ["", "## Weakest companies", "", "| Company | Avg score | Failures |", "|---|---|---|"]
        for w in r["weak_companies"]:
            lines.append(f"| {w['company']} | {w['avg_score']} | {w['failures']} |")
    if r["boilerplate_clusters"]:
        lines += [
            "",
            "## Boilerplate clusters",
            "",
            "| Section | Companies | Similarity |",
            "|---|---|---|",
        ]
        for c in r["boilerplate_clusters"][:30]:
            lines.append(f"| {c['section']} | {' vs '.join(c['companies'])} | {c['similarity']} |")
    lines += ["", "## Worst 50 answers", "", "| ID | Score | Question | Reasons |", "|---|---|---|---|"]
    for w in r["worst_answers"]:
        lines.append(
            f"| {w['id']} | {w['score']} | {w['question'][:60]} | {', '.join(w['fails']) or '—'} |"
        )
    return "\n".join(lines) + "\n"


def _html(r: dict[str, Any]) -> str:
    colour = "#1f7a4d" if r["decision"] == "PASS" else "#b42318"

    def heat(v: float) -> str:
        if v >= 90:
            return "#e6f4ec"
        if v >= 70:
            return "#fdf5e3"
        return "#fdeceb"

    sections = "".join(
        f"<tr><td>{escape(SECTION_TITLES.get(k, k))}</td>"
        f"<td style='background:{heat(v)}'>{v}%</td>"
        f"<td style='background:{heat(r['section_avg_quality'][k])}'>{r['section_avg_quality'][k]}</td></tr>"
        for k, v in r["section_scores"].items()
    )
    gates = "".join(
        f"<tr><td>{escape(GATE_TITLES.get(k, k))}</td>"
        f"<td style='background:{'#e6f4ec' if v == 0 else '#fdeceb'}'>{v}</td></tr>"
        for k, v in r["gates"].items()
    )
    dims = "".join(
        f"<tr><td>{escape(d.replace('_', ' '))}</td>"
        f"<td style='background:{heat(v)}'>{v}%</td></tr>"
        for d, v in r["dimension_avg"].items()
    )
    weak = "".join(
        f"<tr><td>{escape(w['company'])}</td><td>{w['avg_score']}</td><td>{w['failures']}</td></tr>"
        for w in r["weak_companies"]
    )
    clusters = "".join(
        f"<tr><td>{escape(c['section'])}</td><td>{escape(' vs '.join(c['companies']))}</td>"
        f"<td>{c['similarity']}</td><td>{escape(c['answer'][:120])}</td></tr>"
        for c in r["boilerplate_clusters"][:40]
    )
    worst = "".join(
        f"<tr><td>{escape(w['id'])}</td><td>{w['score']}</td>"
        f"<td>{escape(w['question'][:70])}</td><td>{escape(', '.join(w['fails']) or '—')}</td>"
        f"<td>{escape(w['answer'][:140])}</td></tr>"
        for w in r["worst_answers"]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AGI Answer Quality Acceptance v1.0</title>
<style>
 body {{ font-family: 'IBM Plex Sans', system-ui, sans-serif; margin: 2rem; color: #142033; }}
 h1 {{ margin-bottom: .2rem; }} h2 {{ margin-top: 2rem; }}
 .score {{ font-size: 2.5rem; font-weight: 700; color: {colour}; }}
 table {{ border-collapse: collapse; margin: .75rem 0; }}
 th, td {{ border: 1px solid #d7dee8; padding: .4rem .65rem; font-size: .88rem; text-align: left; }}
 th {{ background: #f3f6fa; }}
 .muted {{ color: #5b6b7c; font-size: .85rem; }}
</style></head><body>
<h1>AGI Answer Quality Acceptance v1.0</h1>
<p class="muted">Generated {escape(r['generated_at'])}</p>
<p class="score">{r['overall_score']}% — {escape(r['decision'])}</p>
<p class="muted">{r['passed']}/{r['total']} answers at or above quality {r['case_pass_score']}; target {r['target_pct']}%</p>
<h2>Section quality heatmap</h2>
<table><tr><th>Section</th><th>Pass rate</th><th>Avg quality</th></tr>{sections}</table>
<h2>Quality gates</h2><table><tr><th>Gate</th><th>Count</th></tr>{gates}</table>
<h2>Dimension averages</h2><table><tr><th>Dimension</th><th>Score</th></tr>{dims}</table>
<h2>Weakest companies</h2><table><tr><th>Company</th><th>Avg score</th><th>Failures</th></tr>{weak}</table>
<h2>Boilerplate clusters</h2>
{'<table><tr><th>Section</th><th>Companies</th><th>Similarity</th><th>Answer</th></tr>' + clusters + '</table>' if clusters else '<p><strong>None.</strong></p>'}
<h2>Worst 50 answers</h2>
<table><tr><th>ID</th><th>Score</th><th>Question</th><th>Reasons</th><th>Answer</th></tr>{worst}</table>
</body></html>
"""


def main() -> int:
    limit = int(os.environ.get("AQ_LIMIT") or "0") or None
    print("[answer_quality] running AGI Answer Quality Acceptance v1.0", flush=True)
    report = run(limit=limit)
    report["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    print(f"\n[answer_quality] version={report['version']} n={report['total']}")
    for key, pct in report["section_scores"].items():
        b = report["sections"][key]
        print(
            f"  {SECTION_TITLES.get(key, key):32s} {b['passed']:3d}/{b['total']:<3d} "
            f"({pct}%)  avg quality {b['avg_score']}"
        )
    print("\n  quality gates:")
    for key, count in report["gates"].items():
        print(f"    {GATE_TITLES.get(key, key):32s} {count}")
    print("\n  dimension averages:")
    for dim, val in report["dimension_avg"].items():
        print(f"    {dim:28s} {val}%")
    print(
        f"\n[answer_quality] {report['passed']}/{report['total']} "
        f"({report['overall_score']}%) decision={report['decision']}"
    )

    art_dir = _artifacts_dir()
    write_artifact("answer_quality_acceptance_v1.json", report)
    (art_dir / "answer_quality_acceptance_v1.md").write_text(_markdown(report), encoding="utf-8")
    (art_dir / "answer_quality_acceptance_v1.html").write_text(_html(report), encoding="utf-8")

    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
