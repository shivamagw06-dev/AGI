"""FSE-ECD Mission Control façades — Evidence Coverage Dashboard."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.evidence_coverage.schema import (
    ECD_VERSION,
    FUNNEL_STAGES,
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    STAGE_LABELS,
    STAGE_TARGETS,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.evidence_coverage.stages import assess_company
from financial_statements_engine.evidence_coverage.universe import resolve_universe
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "ecd_version": ECD_VERSION,
        "question": "How many companies do we have?",
        "funnel_stages": list(FUNNEL_STAGES),
        "stage_targets": dict(STAGE_TARGETS),
        "stage_labels": dict(STAGE_LABELS),
        "universes": ["gold", "nifty50", "nifty100", "nifty500", "hd"],
        "default_universe": "nifty500",
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_ECD_EVIDENCE_COVERAGE_DASHBOARD.md",
        "as_of": now_iso(),
    }


def _pct(have: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * have / total, 2)


def dashboard(universe: str = "nifty500", *, include_rows: bool = True, limit: int | None = None) -> dict[str, Any]:
    """Universe funnel: discovered → filings → parsed → validated → published → derived."""
    uni = resolve_universe(universe)
    tickers = list(uni["tickers"])
    if limit is not None:
        tickers = tickers[: max(0, int(limit))]

    rows: list[dict[str, Any]] = []
    counts = {s: 0 for s in FUNNEL_STAGES}
    live_annual = 0
    live_quarterly = 0
    with_any_financial_evidence = 0
    gaps: dict[str, list[str]] = {s: [] for s in FUNNEL_STAGES}

    for t in tickers:
        row = assess_company(t, in_universe=True)
        rows.append(row)
        for s in FUNNEL_STAGES:
            if row["stages"].get(s):
                counts[s] += 1
            else:
                if len(gaps[s]) < 25:
                    gaps[s].append(t)
        ev = row["evidence"]
        if (ev.get("annual_periods") or 0) > 0 or (ev.get("quarterly_periods") or 0) > 0 or ev.get("fse_raw"):
            with_any_financial_evidence += 1
        if ev.get("annual_live"):
            live_annual += 1
        if ev.get("quarterly_live"):
            live_quarterly += 1

    total = len(tickers)
    funnel = []
    for s in FUNNEL_STAGES:
        have = counts[s]
        pct = _pct(have, total)
        funnel.append(
            {
                "stage": s,
                "label": STAGE_LABELS[s],
                "have": have,
                "total": total,
                "pct": pct,
                "target_pct": 100.0,
                "gap_n": total - have,
                "on_target": pct >= 100.0,
                "sample_gaps": gaps[s],
            }
        )

    # Bottleneck = first stage below 100% with largest remaining gap in sequence
    bottleneck = next((f for f in funnel if not f["on_target"]), None)

    out: dict[str, Any] = {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "ecd_version": ECD_VERSION,
        "question": "How many companies do we have?",
        "universe": uni["universe"],
        "universe_size": total,
        "funnel": funnel,
        "summary": {
            "discovered": counts["discovered"],
            "latest_annual_filing": counts["latest_annual_filing"],
            "latest_quarterly_filing": counts["latest_quarterly_filing"],
            "parsed": counts["parsed"],
            "validated": counts["validated"],
            "published": counts["published"],
            "derived_metrics": counts["derived_metrics"],
            "fully_complete": sum(1 for r in rows if r["complete"]),
            "with_any_financial_evidence": with_any_financial_evidence,
            "with_any_financial_evidence_pct": _pct(with_any_financial_evidence, total),
            "live_annual_source_n": live_annual,
            "live_quarterly_source_n": live_quarterly,
            "discovered_means": "universe_membership_for_listed_indices",
        },
        "bottleneck": {
            "stage": bottleneck["stage"] if bottleneck else None,
            "label": bottleneck["label"] if bottleneck else None,
            "have": bottleneck["have"] if bottleneck else total,
            "total": total,
            "pct": bottleneck["pct"] if bottleneck else 100.0,
            "gap_n": bottleneck["gap_n"] if bottleneck else 0,
            "interpretation": (
                f"Primary gap: {bottleneck['label']} at {bottleneck['pct']}% "
                f"({bottleneck['have']}/{total})"
                if bottleneck
                else "All funnel stages at 100% for this universe"
            ),
        },
        "targets": {STAGE_LABELS[s]: "100%" for s in FUNNEL_STAGES},
        "issues_recommendations": False,
        "as_of": now_iso(),
    }
    if include_rows:
        out["rows"] = rows
    return out


def company(ticker: str) -> dict[str, Any]:
    row = assess_company(ticker, in_universe=True)
    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "ecd_version": ECD_VERSION,
        "company": row,
        "as_of": now_iso(),
    }
