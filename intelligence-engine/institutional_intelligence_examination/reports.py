"""Build markdown / grades artifacts for IIEX."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_grades(run: dict[str, Any]) -> dict[str, Any]:
    summary = run.get("summary") or {}
    return {
        "run_id": run.get("run_id"),
        "version": run.get("version"),
        "generated_at": run.get("generated_at"),
        "marks_available": summary.get("marks_available"),
        "marks_awarded": summary.get("marks_awarded"),
        "pct": summary.get("pct"),
        "normalized_500": summary.get("normalized_500"),
        "passed": summary.get("passed"),
        "certification": summary.get("certification"),
        "dimension_scores": summary.get("dimension_scores"),
        "by_section": summary.get("by_section"),
        "per_question": [
            {
                "id": r["question"]["id"],
                "section": r["question"]["section"],
                "title": r["question"]["title"],
                "marks_available": r["score"]["marks_available"],
                "marks_awarded": r["score"]["marks_awarded"],
                "pct": r["score"]["pct"],
                "sources": r["evidence_pack"].get("sources"),
            }
            for r in run.get("results") or []
        ],
        "providers_queried": [],
        "internet_used": False,
    }


def build_markdown(run: dict[str, Any]) -> str:
    s = run.get("summary") or {}
    lines = [
        "# AGI Institutional Intelligence Examination (IIE) v1.0 — Report",
        "",
        f"**Programme:** {run.get('programme')} (`{run.get('programme_short')}`)",
        f"**Run ID:** `{run.get('run_id')}`",
        f"**Generated:** {run.get('generated_at')}",
        f"**Method:** AGIB Intelligence Platform only — no internet search",
        "",
        "---",
        "",
        "## Verdict",
        "",
        f"### Normalized score: **{s.get('normalized_500')} / 500**",
        "",
        f"| Raw marks | {s.get('marks_awarded')} / {s.get('marks_available')} ({s.get('pct')}%) |",
        f"| Pass bar | 450 / 500 (90%) |",
        f"| Certification | **{s.get('certification')}** |",
        f"| Passed | **{s.get('passed')}** |",
        "",
        "### Design",
        "",
        "> This is a CIO Investment Committee Assessment — not a university paper.",
        "> Passing requires end-to-end institutional reasoning across Company, Market,",
        "> Macro, Sector, IPO, Relationship, Historical, Forecast, Research and Portfolio modules.",
        "",
        "---",
        "",
        "## Section scores",
        "",
        "| Section | Awarded | Available | % |",
        "|---|---:|---:|---:|",
    ]
    for sec, b in (s.get("by_section") or {}).items():
        lines.append(f"| {sec} | {b.get('awarded')} | {b.get('available')} | {b.get('pct')} |")

    lines += [
        "",
        "## Final evaluation dimensions (/500)",
        "",
        "| Dimension | Weight | Avg % | Marks |",
        "|---|---:|---:|---:|",
    ]
    for dim, row in (s.get("dimension_scores") or {}).items():
        lines.append(
            f"| {dim} | {row.get('weight')} | {row.get('avg_pct')} | {row.get('marks')} |"
        )
    lines.append(f"| **Total** | 500 | — | **{s.get('dimension_total_500')}** |")

    lines += [
        "",
        "---",
        "",
        "## Per-question scorecard",
        "",
        "| ID | Title | Marks | % | Sources |",
        "|---|---|---:|---:|---|",
    ]
    for r in run.get("results") or []:
        src = ", ".join(r["evidence_pack"].get("sources") or [])
        lines.append(
            f"| {r['question']['id']} | {r['question']['title'][:48]} | "
            f"{r['score']['marks_awarded']}/{r['score']['marks_available']} | "
            f"{r['score']['pct']} | {src} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Guardrails",
        "",
        f"- Internet used: `{run.get('internet_used')}`",
        f"- Providers queried: `{run.get('providers_queried')}`",
        f"- Negative marks: `{run.get('negative_marks')}`",
        f"- Resources: {', '.join(run.get('resources_allowed') or [])}",
        "",
        "## North star",
        "",
        "AGIB competes with institutional platforms only when it can integrate every",
        "intelligence module into coherent, evidence-backed investment committee work.",
        "",
    ]
    return "\n".join(lines)


def write_docs(run: dict[str, Any]) -> dict[str, str]:
    """Persist exam report + grades under docs/ (best-effort)."""
    root = Path(__file__).resolve().parents[2]
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    md_path = docs / "AGIB_IIEX_EXAM_REPORT_v1.md"
    grades_path = docs / "AGIB_IIEX_EXAM_GRADES_v1.json"
    md_path.write_text(build_markdown(run), encoding="utf-8")
    grades_path.write_text(json.dumps(build_grades(run), indent=2), encoding="utf-8")
    written = {"markdown": str(md_path), "grades": str(grades_path)}
    try:
        art = Path("/opt/cursor/artifacts/agi-iiex-v1")
        art.mkdir(parents=True, exist_ok=True)
        (art / "EXAM_REPORT.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
        (art / "grades.json").write_text(grades_path.read_text(encoding="utf-8"), encoding="utf-8")
        summary = {
            "run_id": run.get("run_id"),
            "normalized_500": (run.get("summary") or {}).get("normalized_500"),
            "certification": (run.get("summary") or {}).get("certification"),
            "passed": (run.get("summary") or {}).get("passed"),
            "internet_used": run.get("internet_used"),
            "providers_queried": run.get("providers_queried"),
        }
        (art / "raw_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        written["artifacts"] = str(art)
    except Exception:
        pass
    return written
