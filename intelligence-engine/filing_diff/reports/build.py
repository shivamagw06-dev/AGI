"""Filing Diff Report — change intelligence, not filing summary."""

from __future__ import annotations

from typing import Any

from filing_diff.schema import FDI_VERSION

_MAT_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "ignore": 9}


def build_report(
    *,
    ticker: str,
    ctx: dict[str, Any],
    changes: list[dict[str, Any]],
    confidence: dict[str, Any],
    evidence: dict[str, Any],
    thesis_matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    material = [
        c for c in changes
        if not c.get("cosmetic") and c.get("materiality") not in {"ignore", None}
    ]
    material.sort(key=lambda c: (_MAT_ORDER.get(c.get("materiality") or "low", 5), c.get("domain") or ""))

    def _domain(name: str) -> list[dict[str, Any]]:
        return [c for c in material if c.get("domain") == name]

    top10 = material[:10]
    thesis = {
        "strengthens_thesis": sum(1 for c in material if c.get("thesis_impact") == "strengthens_thesis"),
        "weakens_thesis": sum(1 for c in material if c.get("thesis_impact") == "weakens_thesis"),
        "neutral": sum(1 for c in material if c.get("thesis_impact") == "neutral"),
        "unknown": sum(1 for c in material if c.get("thesis_impact") == "unknown"),
        "needs_committee_review": sum(
            1 for c in material if c.get("thesis_impact") == "needs_committee_review"
        ),
    }
    matrix = thesis_matrix or {}
    open_q = []
    for c in top10:
        open_q.extend(c.get("open_questions") or [])
    # dedupe
    seen = set()
    open_questions = []
    for q in open_q:
        if q not in seen:
            seen.add(q)
            open_questions.append(q)

    exec_bits = [
        f"Filing Diff — {ticker}: what changed from {ctx.get('previous_period')} → {ctx.get('current_period')}.",
        f"Material changes: {len(material)} (critical/high: "
        f"{sum(1 for c in material if c.get('materiality') in {'critical','high'})}).",
    ]
    for c in top10[:5]:
        tim = c.get("thesis_impact_matrix") or {}
        exec_bits.append(
            f"- [{c.get('materiality')}] {c.get('metric')}: {c.get('change_type')} "
            f"({c.get('previous_value')} → {c.get('current_value')}); "
            f"B{tim.get('business','?')} F{tim.get('financial','?')} "
            f"V{tim.get('valuation','?')} R{tim.get('risk','?')} → {tim.get('committee','Review')}"
        )

    committee = {
        "material_changes": top10,
        "evidence_count": evidence.get("linked_count"),
        "historical_context": {
            "previous_period": ctx.get("previous_period"),
            "current_period": ctx.get("current_period"),
            "mode": (ctx.get("comparison_pair") or {}).get("mode"),
        },
        "potential_thesis_impact": thesis,
        "thesis_impact_matrix": matrix,
        "committee_queue": matrix.get("committee_queue") or {},
        "open_questions": open_questions[:8],
        "required_follow_up": [
            "Confirm whether NIM/CASA moves are structural vs cyclical with next-quarter liability mix",
            "Reconciliation of guidance language vs margin commentary",
            "Peer sync check via PIL after FIL refresh",
        ],
    }

    escalate_n = len((matrix.get("committee_queue") or {}).get("escalate") or [])
    review_n = len((matrix.get("committee_queue") or {}).get("review") or [])

    lines = [
        f"Filing Diff Report — {ticker}",
        f"FDI {FDI_VERSION}",
        "",
        "PRIMARY QUESTION",
        "What materially changed since the previous filing?",
        "",
        "EXECUTIVE SUMMARY",
        *exec_bits,
        "",
        "THESIS IMPACT MATRIX",
        matrix.get("markdown_table") or "(none)",
        "",
        "INVESTMENT THESIS IMPACT (no buy/sell)",
        str(thesis),
        "",
        "CONFIDENCE",
        confidence.get("explain") or "",
        "",
        "MISSING EVIDENCE",
        "Full prior-quarter transcript wording diff pending denser FIL corpus.",
    ]

    return {
        "ticker": ticker,
        "fdi_version": FDI_VERSION,
        "executive_summary": "\n".join(exec_bits),
        "top_10_material_changes": top10,
        "financial_changes": _domain("statement"),
        "management_changes": _domain("management"),
        "risk_changes": _domain("risks"),
        "guidance_changes": _domain("guidance"),
        "capital_allocation_changes": _domain("capital"),
        "governance_changes": _domain("governance"),
        "accounting_changes": _domain("accounting") + _domain("notes"),
        "segment_changes": _domain("segment"),
        "ownership_changes": _domain("ownership"),
        "investment_thesis_impact": thesis,
        "thesis_impact_matrix": matrix,
        "confidence": confidence,
        "missing_evidence": [
            "Full multi-quarter transcript corpus",
            "Page-level PDF anchors for all qualitative diffs",
        ],
        "committee": committee,
        "cio_brief": (
            f"What changed ({ctx.get('previous_period')}→{ctx.get('current_period')}): "
            f"{len(material)} material items; "
            f"weakens={thesis['weakens_thesis']}, strengthens={thesis['strengthens_thesis']}; "
            f"matrix queue escalate={escalate_n}, review={review_n}."
        ),
        "text": "\n".join(lines),
        "rule": "Never recommend Buy or Sell; classify thesis impact only",
    }
