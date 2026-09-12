"""Markdown / JSON reports for IST runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def build_markdown(result: Mapping[str, Any]) -> str:
    score = result.get("score") or {}
    orch = score.get("orchestration") or {}
    rubric = score.get("rubric") or {}
    lines = [
        f"# {result.get('case_id')} — {result.get('title')}",
        "",
        f"**Question:** {result.get('question')}",
        "",
        f"**Result:** {'PASS' if result.get('passed') else 'FAIL'}",
        f"**Score:** {score.get('weighted_total')} / 100 (pass ≥ {score.get('pass_score')})",
        "",
        "## Orchestration gate",
        "",
        f"- Contribution ratio: {orch.get('contribution_ratio')}",
        f"- Required hit: {', '.join(orch.get('required_hit') or []) or '—'}",
        f"- Missing required: {', '.join(orch.get('missing_required') or []) or 'none'}",
        f"- Single-module: {orch.get('single_module')}",
        f"- Failures: {', '.join(score.get('automatic_failures') or []) or 'none'}",
        "",
        "> No individual module can pass this stress test on its own.",
        "",
        "## Rubric",
        "",
        "| Area | Weight | Score | Points |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rubric.get("breakdown") or []:
        lines.append(
            f"| {row.get('area')} | {row.get('weight')} | {row.get('score_0_1')} | {row.get('points')} |"
        )
    lines.extend(
        [
            "",
            "## Final Institutional View (shape)",
            "",
            "Investment Thesis · Evidence Supporting · Evidence Against · Remaining Unknowns · "
            "Confidence · Evidence References · Questions requiring monitoring",
            "",
            "**Not** BUY / SELL.",
            "",
            f"_{score.get('summary')}_",
            "",
        ]
    )
    return "\n".join(lines)


def write_docs(result: Mapping[str, Any], *, docs_root: str | Path | None = None) -> dict[str, str]:
    # institutional_stress_tests/ → intelligence-engine/ → repo root
    root = Path(docs_root or Path(__file__).resolve().parents[2] / "docs")
    root.mkdir(parents=True, exist_ok=True)
    case_id = str(result.get("case_id") or "IST-01").replace("-", "_")
    md_path = root / f"AGI_{case_id}_REPORT.md"
    json_path = root / f"AGI_{case_id}_GRADES.json"
    md = build_markdown(result)
    md_path.write_text(md, encoding="utf-8")
    import json

    payload = {
        "case_id": result.get("case_id"),
        "passed": result.get("passed"),
        "weighted_total": (result.get("score") or {}).get("weighted_total"),
        "automatic_failures": (result.get("score") or {}).get("automatic_failures"),
        "gates": (result.get("score") or {}).get("gates"),
        "orchestration": (result.get("score") or {}).get("orchestration"),
        "rubric": (result.get("score") or {}).get("rubric"),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {"markdown": str(md_path), "grades": str(json_path)}
