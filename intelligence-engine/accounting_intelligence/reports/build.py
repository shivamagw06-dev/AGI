"""ACI report builder — institutional output format."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    profile: dict[str, Any],
    confidence: dict[str, Any],
    earnings: dict[str, Any],
    cash: dict[str, Any],
    accruals: dict[str, Any],
    revenue: dict[str, Any],
    working_capital: dict[str, Any],
    balance_sheet: dict[str, Any],
    policies: dict[str, Any],
    forensic: dict[str, Any],
    manipulation: dict[str, Any],
    behaviour: dict[str, Any],
    thesis_events: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    conf = confidence.get("confidence")
    company = profile.get("company") or profile.get("ticker")
    exec_sum = (
        f"{company}: accounting confidence {conf}/100. "
        f"Earnings quality {earnings.get('label')}; cash conversion {cash.get('cash_conversion')}; "
        f"accruals {accruals.get('label')}; behaviour **{behaviour.get('primary')}**. "
        f"Primary question: can the reported numbers be trusted?"
    )
    aq_score = round(
        (
            float(cash.get("cash_quality") or 0) * 0.3
            + float(earnings.get("earnings_quality") or 0) * 0.25
            + float(working_capital.get("working_capital") or 0) * 0.15
            + float(policies.get("accounting_consistency") or 0) * 0.15
            + float(forensic.get("forensic") or 0) * 0.15
        ),
        1,
    )
    cio_brief = (
        f"Institutional accounting assessment: quality score {aq_score}/100, "
        f"manipulation risk {manipulation.get('manipulation_risk')}, "
        f"Beneish M {((forensic.get('beneish') or {}).get('beneish_m'))}, "
        f"Piotroski F {((forensic.get('piotroski') or {}).get('piotroski_f'))}. "
        f"{behaviour.get('narrative')}"
    )
    return {
        "executive_summary": exec_sum,
        "accounting_quality_score": aq_score,
        "accounting_quality": {
            "score": aq_score,
            "confidence": conf,
            "earnings_quality": earnings.get("earnings_quality"),
            "cash_quality": cash.get("cash_quality"),
            "working_capital": working_capital.get("working_capital"),
            "accounting_consistency": policies.get("accounting_consistency"),
            "forensic": forensic.get("forensic"),
            "behaviour": behaviour.get("primary"),
        },
        "earnings_quality": earnings,
        "cash_quality": cash,
        "revenue_recognition": revenue,
        "working_capital": working_capital,
        "balance_sheet": balance_sheet,
        "accounting_policy_changes": policies,
        "forensic_review": forensic,
        "manipulation_risk": manipulation,
        "behaviour": behaviour,
        "historical_trend": "see timeline",
        "confidence": confidence,
        "evidence": evidence,
        "missing_evidence": evidence.get("missing") or confidence.get("unknowns") or [],
        "thesis_impact_events": thesis_events,
        "cio_brief": cio_brief,
        "committee": {
            "dashboard": {
                "score": aq_score,
                "manipulation_risk": manipulation.get("manipulation_risk"),
                "behaviour": behaviour.get("primary"),
                "alert_count": manipulation.get("alert_count"),
            },
            "red_flags": [a.get("flag") for a in (manipulation.get("alerts") or [])],
            "quality_trend": behaviour.get("primary"),
        },
        "text": exec_sum + " " + cio_brief,
    }
