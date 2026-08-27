"""Opportunity blockers — factors limiting research conviction (not sell signals)."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.util import as_float


def detect_blockers(
    memory: dict[str, Any],
    *,
    dimensions: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    vh = memory.get("valuation_history") or {}
    fh = memory.get("financial_history") or {}
    oh = memory.get("ownership_history") or {}
    risk = memory.get("risk_history") or {}

    premium = as_float(((vh.get("relative") or {}).get("pe") or {}).get("premium_pct"))
    pct = as_float(((vh.get("historical_bands") or {}).get("pe") or {}).get("percentile"))
    if premium is not None and premium > 25:
        blockers.append(
            {
                "code": "rich_valuation",
                "severity": "High",
                "title": "Rich valuation vs peers",
                "detail": f"Peer premium {premium:.1f}%",
                "evidence_path": "valuation_history.relative.pe.premium_pct",
                "score_penalty": 12,
            }
        )
    if pct is not None and pct >= 85:
        blockers.append(
            {
                "code": "expensive_history",
                "severity": "Medium",
                "title": "Elevated historical valuation percentile",
                "detail": f"PE percentile {pct:.0f}",
                "evidence_path": "valuation_history.historical_bands.pe.percentile",
                "score_penalty": 8,
            }
        )

    ocf_q = as_float(((fh.get("cash_flow") or {}).get("quality_ocf_to_pat")))
    if ocf_q is not None and ocf_q < 0.5:
        blockers.append(
            {
                "code": "weak_earnings_quality",
                "severity": "High",
                "title": "Weak cash-flow quality vs PAT",
                "detail": f"OCF/PAT {ocf_q:.2f}",
                "evidence_path": "financial_history.cash_flow.quality_ocf_to_pat",
                "score_penalty": 10,
            }
        )

    rev_yoy = as_float((fh.get("revenue") or {}).get("yoy"))
    if rev_yoy is not None and rev_yoy < 0:
        blockers.append(
            {
                "code": "weak_demand",
                "severity": "High",
                "title": "Revenue contraction",
                "detail": f"Revenue YoY {rev_yoy:.1f}%",
                "evidence_path": "financial_history.revenue.yoy",
                "score_penalty": 10,
            }
        )

    trend = str((fh.get("ebitda") or {}).get("trend") or "").lower()
    if "deterior" in trend or "compress" in trend:
        blockers.append(
            {
                "code": "margin_deterioration",
                "severity": "Medium",
                "title": "Margin deterioration",
                "detail": trend,
                "evidence_path": "financial_history.ebitda.trend",
                "score_penalty": 8,
            }
        )

    pledge = as_float((oh.get("latest") or {}).get("pledge") or (oh.get("latest") or {}).get("promoter_pledge_pct"))
    if pledge is not None and pledge >= 20:
        blockers.append(
            {
                "code": "governance_pledge",
                "severity": "High",
                "title": "Governance concern — elevated promoter pledge",
                "detail": f"Pledge {pledge:.1f}%",
                "evidence_path": "ownership_history.latest.pledge",
                "score_penalty": 14,
            }
        )

    debt = as_float(((fh.get("debt") or {}).get("debt_to_equity")))
    if debt is not None and debt >= 1.5:
        blockers.append(
            {
                "code": "debt_stress",
                "severity": "Medium",
                "title": "Elevated leverage",
                "detail": f"D/E {debt:.2f}",
                "evidence_path": "financial_history.debt.debt_to_equity",
                "score_penalty": 8,
            }
        )

    stretch = risk.get("valuation_stretch") or risk.get("leverage")
    if stretch:
        blockers.append(
            {
                "code": "risk_flag",
                "severity": "Medium",
                "title": "Risk history flag present",
                "detail": str(stretch)[:120],
                "evidence_path": "risk_history",
                "score_penalty": 6,
            }
        )

    # Low dimension scores as soft blockers
    for key, title in (
        ("financial_momentum", "Weak financial momentum profile"),
        ("ownership_momentum", "Weak ownership momentum profile"),
    ):
        dim = dimensions.get(key) or {}
        sc = as_float(dim.get("score"))
        if sc is not None and sc < 35 and dim.get("available"):
            blockers.append(
                {
                    "code": f"weak_{key}",
                    "severity": "Low",
                    "title": title,
                    "detail": f"Dimension score {sc:.0f}",
                    "evidence_path": key,
                    "score_penalty": 4,
                }
            )

    # Deterministic order
    sev = {"High": 0, "Medium": 1, "Low": 2}
    blockers.sort(key=lambda b: (sev.get(b.get("severity") or "", 9), b.get("code") or ""))
    return blockers
