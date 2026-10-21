"""Financial Intelligence Report assembly (sections 1–13)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.confidence import confidence_distribution
from financial_intelligence.findings import assert_no_hallucination, findings_from_series
from financial_intelligence.inventory import load_metric_series
from financial_intelligence.schema import (
    CONF_HIGH,
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REPORT_SECTIONS,
    SEV_NEGATIVE,
    SEV_POSITIVE,
    SEV_WARNING,
    SPEC,
    VERSION,
    WORKSTREAM_ID,
)
try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _coverage_pct(coverage: dict[str, Any]) -> float | None:
    if not coverage:
        return None
    for key in ("overall_completeness_pct", "coverage_pct", "average_coverage_pct"):
        if isinstance(coverage.get(key), (int, float)):
            return float(coverage[key])
    cov = coverage.get("coverage") or {}
    if isinstance(cov.get("coverage_pct"), (int, float)):
        return float(cov["coverage_pct"])
    return None


def _section_text(findings: list[dict[str, Any]], category: str) -> dict[str, Any]:
    rows = [f for f in findings if f.get("category") == category]
    narratives = [f.get("narrative") for f in rows if f.get("narrative")]
    return {
        "section": category,
        "n_findings": len(rows),
        "narratives": narratives,
        "findings": rows,
        "prose": " ".join(narratives) if narratives else None,
    }


def build_report(ticker: str, *, series_map: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Build full FIR. Pass series_map in tests to avoid warehouse dependency."""
    t = ticker.upper().strip()
    inv: dict[str, Any]
    if series_map is not None:
        inv = {
            "ticker": t,
            "series": series_map,
            "warehouse_version": None,
            "coverage": {},
            "validation": {},
            "notes": [],
            "read_only": True,
            "mutated_warehouse": False,
        }
    else:
        inv = load_metric_series(t)

    cov_pct = _coverage_pct(inv.get("coverage") or {})
    findings = assert_no_hallucination(
        findings_from_series(inv.get("series") or {}, coverage_pct=cov_pct, ticker=t)
    )

    positives = [f for f in findings if f.get("severity") == SEV_POSITIVE]
    negatives = [f for f in findings if f.get("severity") in {SEV_NEGATIVE, SEV_WARNING}]
    high_conf = [f for f in findings if f.get("confidence") == CONF_HIGH]
    warnings = [f for f in findings if f.get("severity") in {SEV_WARNING, SEV_NEGATIVE}]

    sections: dict[str, Any] = {}
    for sec in REPORT_SECTIONS:
        if sec == "executive_summary":
            top = findings[:5]
            sections[sec] = {
                "section": sec,
                "prose": " ".join(f["narrative"] for f in top if f.get("narrative")) or None,
                "findings": top,
                "n_findings": len(top),
            }
        elif sec == "key_positives":
            sections[sec] = {
                "section": sec,
                "prose": " ".join(f["narrative"] for f in positives) or None,
                "findings": positives,
                "n_findings": len(positives),
            }
        elif sec == "key_negatives":
            sections[sec] = {
                "section": sec,
                "prose": " ".join(f["narrative"] for f in negatives) or None,
                "findings": negatives,
                "n_findings": len(negatives),
            }
        elif sec == "risks":
            risk_rows = [f for f in findings if f.get("severity") in {SEV_WARNING, SEV_NEGATIVE}]
            sections[sec] = {
                "section": sec,
                "prose": " ".join(f["narrative"] for f in risk_rows) or None,
                "findings": risk_rows,
                "n_findings": len(risk_rows),
            }
        elif sec == "overall_financial_assessment":
            n_pos, n_neg = len(positives), len(negatives)
            if not findings:
                prose = "Insufficient validated warehouse history to form an evidence-backed assessment."
            elif n_pos > n_neg:
                prose = (
                    f"Evidence-backed assessment leans constructive on {n_pos} positive finding(s) "
                    f"versus {n_neg} cautionary finding(s). No recommendation is issued."
                )
            elif n_neg > n_pos:
                prose = (
                    f"Evidence-backed assessment surfaces {n_neg} cautionary finding(s) "
                    f"versus {n_pos} positive finding(s). No recommendation is issued."
                )
            else:
                prose = (
                    f"Evidence-backed assessment is balanced ({n_pos} positive / {n_neg} cautionary). "
                    "No recommendation is issued."
                )
            sections[sec] = {
                "section": sec,
                "prose": prose,
                "findings": findings,
                "n_findings": len(findings),
            }
        else:
            sections[sec] = _section_text(findings, sec)

    dist = confidence_distribution(findings)
    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": VERSION,
        "ticker": t,
        "executive_summary": sections.get("executive_summary"),
        "sections": sections,
        "findings": findings,
        "evidence": {
            "warehouse_version": inv.get("warehouse_version"),
            "series_metrics": sorted(k for k, v in (inv.get("series") or {}).items() if v),
            "coverage": {
                "coverage_pct": cov_pct,
                "raw": {k: inv.get("coverage", {}).get(k) for k in ("overall_completeness_pct", "coverage_pct", "ticker") if isinstance(inv.get("coverage"), dict)},
            },
            "validation_reports_n": (inv.get("validation") or {}).get("n"),
        },
        "confidence": {
            "distribution": dist,
            "high_confidence_findings": high_conf,
        },
        "warnings": warnings,
        "mission_control": {
            "financial_findings": len(findings),
            "high_confidence_findings": len(high_conf),
            "warnings": len(warnings),
            "evidence_coverage_pct": cov_pct,
            "confidence_distribution": dist,
        },
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "mutated_warehouse": False,
        "spec": SPEC,
        "as_of": now_iso(),
        "inventory_notes": inv.get("notes") or [],
    }
