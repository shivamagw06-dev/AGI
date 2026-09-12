"""FDI analyse pipeline — compare periods, emit material change intelligence."""

from __future__ import annotations

from typing import Any

from filing_diff.capital_allocation_diff.diff import capital_allocation_diff
from filing_diff.comparator.periods import load_comparison_context
from filing_diff.confidence.score import score_diff
from filing_diff.evidence.attach import evidence_for_changes
from filing_diff.governance_diff.diff import governance_diff
from filing_diff.guidance_diff.diff import guidance_diff
from filing_diff.management_diff.diff import management_diff
from filing_diff.notes_diff.diff import notes_diff
from filing_diff.ownership_diff.diff import ownership_diff
from filing_diff.reports.build import build_report
from filing_diff.risks_diff.diff import risks_diff
from filing_diff.schema import FDI_VERSION
from filing_diff.segment_diff.diff import segment_diff
from filing_diff.statement_diff.diff import statement_diff
from filing_diff.thesis_matrix.matrix import build_thesis_impact_matrix
from filing_diff.timeline.build import build_change_timeline


def analyse_diff(ticker: str) -> dict[str, Any]:
    ctx = load_comparison_context(ticker)
    if not ctx.get("found"):
        return {"ticker": ticker.upper(), "found": False, "fdi_version": FDI_VERSION}

    records = []
    records += statement_diff(ctx)
    note_rows = notes_diff(ctx)
    for r in note_rows:
        if "Impairment" in r.metric or "Revenue_Recognition" in r.metric or "Accounting_Policy" in r.metric:
            r.domain = "accounting"
    records += note_rows
    records += guidance_diff(ctx)
    records += management_diff(ctx)
    records += risks_diff(ctx)
    records += segment_diff(ctx)
    records += capital_allocation_diff(ctx)
    records += governance_diff(ctx)
    records += ownership_diff(ctx)

    changes = [r.to_dict() for r in records]
    changes = [_apply_negation_filter(c, ctx) for c in changes]
    # drop ignores / cosmetics from primary list but keep audit
    material = [c for c in changes if not c.get("cosmetic") and c.get("materiality") != "ignore"]
    thesis_matrix = build_thesis_impact_matrix(material)
    confidence = score_diff(changes)
    evidence = evidence_for_changes(material, ctx.get("documents") or [])
    # attach prior doc stub into evidence docs list for linkage display
    docs = list(ctx.get("documents") or [])
    prev_docs = ((ctx.get("qual_by_period") or {}).get(ctx.get("previous_period") or "") or {}).get("docs") or []
    for d in prev_docs:
        if d and not any(x.get("doc_id") == d for x in docs):
            docs.append({"doc_id": d, "title": d, "as_of": "", "evidence_tier": 2})
    evidence = evidence_for_changes(material, docs)
    timeline = build_change_timeline(material, ctx)
    report = build_report(
        ticker=ctx["ticker"],
        ctx=ctx,
        changes=changes,
        confidence=confidence,
        evidence=evidence,
        thesis_matrix=thesis_matrix,
    )

    return {
        "ticker": ctx["ticker"],
        "found": True,
        "fdi_version": FDI_VERSION,
        "primary_question": "What materially changed since the previous filing?",
        "comparison": ctx.get("comparison_pair"),
        "current_period": ctx.get("current_period"),
        "previous_period": ctx.get("previous_period"),
        "changes": material,
        "all_detected": changes,
        "thesis_impact_matrix": thesis_matrix,
        "timeline": timeline,
        "evidence": evidence,
        "confidence": confidence,
        "report": report,
        "origin": "filing_diff_engine",
    }


_NEGATION_METRICS = {
    "Buybacks": ("buyback not", "buybacks not", "no buyback"),
    "Acquisitions": ("no acquisition",),
    "Capital_Raises": ("no extraordinary capital raise", "no capital raise"),
    "Revenue_Recognition": ("no material revenue recognition", "revenue recognition change"),
}


def _apply_negation_filter(change: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Downgrade false-positive adds when filing text negates the action."""
    if change.get("change_type") not in {"buyback", "acquisition_announced", "capital_raise", "policy_added"}:
        return change
    metric = change.get("metric") or ""
    try:
        from filing_intelligence.ingestion.store import documents_for

        texts = [
            str(doc.get("text") or "").lower()
            for doc in documents_for(ctx.get("ticker") or "")
            if doc.get("period") == ctx.get("current_period")
        ]
    except Exception:
        texts = []
    blob = " ".join(texts)

    if change.get("domain") in {"notes", "accounting"} and change.get("change_type") == "policy_added":
        if any(
            phrase in blob
            for phrase in (
                "unchanged vs prior",
                "exceptional items nil",
                "no material revenue recognition",
                "related party and contingent items unchanged",
            )
        ):
            return {**change, "materiality": "ignore", "cosmetic": True, "notes_filter": "unchanged_disclosure"}

    if metric == "Revenue_Recognition" and "no material revenue recognition" in blob:
        return {**change, "materiality": "ignore", "cosmetic": True, "notes_filter": "negation"}
    if metric == "Buybacks" and ("buybacks not announced" in blob or "buyback not announced" in blob):
        return {**change, "materiality": "ignore", "cosmetic": True, "notes_filter": "negation"}
    if metric == "Capital_Raises" and "no extraordinary capital raise" in blob:
        return {**change, "materiality": "ignore", "cosmetic": True, "notes_filter": "negation"}
    if metric == "Acquisitions" and "merger" in blob:
        if "acquisition announced" not in blob and "acquires" not in blob:
            return {**change, "materiality": "ignore", "cosmetic": True, "notes_filter": "negation"}
    return change
