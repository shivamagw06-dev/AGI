"""Soft LEO evidence packages from new Yahoo financial statements (no LEO redesign)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

from yfp.history import summarize_changes
from yfp.schema import YFP_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eid(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return "yfp_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def evidence_from_financial_intelligence(
    ticker: str,
    *,
    financial_history: Dict[str, Any] | None = None,
    valuation_snapshot: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Generate LEO-shaped evidence objects for financial / valuation changes."""
    t = (ticker or "").upper()
    objects: List[Dict[str, Any]] = []
    fh = financial_history or {}
    vs = valuation_snapshot or {}
    changes = summarize_changes(fh) if fh else {}

    facts: List[Dict[str, Any]] = []
    for key, label in (
        ("revenue_growth_pct", "Revenue growth"),
        ("ebitda_growth_pct", "EBITDA growth"),
        ("net_income_growth_pct", "Net income growth"),
        ("ocf_growth_pct", "Operating cash flow growth"),
        ("fcf_growth_pct", "Free cash flow growth"),
        ("debt_change_pct", "Total debt change"),
        ("equity_change_pct", "Equity change"),
    ):
        if changes.get(key) is not None:
            facts.append(
                {
                    "field": key,
                    "value": changes.get(key),
                    "value_text": f"{label}: {changes.get(key)}%",
                    "confidence": 0.72,
                }
            )
    counts = fh.get("counts") or {}
    if any(int(counts.get(k) or 0) > 0 for k in counts):
        facts.append(
            {
                "field": "statements_available",
                "value": True,
                "value_text": (
                    f"annual income={counts.get('income_annual', 0)} "
                    f"balance={counts.get('balance_annual', 0)} "
                    f"cashflow={counts.get('cashflow_annual', 0)}"
                ),
                "confidence": 0.75,
            }
        )
    if facts:
        objects.append(
            {
                "evidence_id": _eid("fs", t, str(counts)),
                "leo_version": "leo-v1.0.0",
                "yfp_version": YFP_VERSION,
                "evidence_type": "financial_statements",
                "fact_key": "financial_changes",
                "value_text": "; ".join(f.get("value_text") or "" for f in facts)[:800],
                "value": changes,
                "entity": t,
                "company_symbol": t,
                "source_id": "yahoo",
                "source_name": "YAHOO",
                "title": f"{t} financial statement history (canonical)",
                "url": "",
                "published": _now(),
                "extracted_facts": facts[:20],
                "confidence": 0.74,
                "verification_status": "provisionally_verified",
                "rank_weight": 1.1,
                "provenance": {
                    "source_id": "yahoo",
                    "connector": "yfp",
                    "fetched_at": _now(),
                    "orchestrator": "YFP",
                },
                "metadata": {
                    "kind": "financial_history",
                    "completed_by": "yfp",
                    "changes": changes,
                },
                "version": 1,
            }
        )

    val_facts = []
    metrics = vs.get("metrics") or {}
    for field in (
        "trailing_pe",
        "forward_pe",
        "enterprise_value",
        "ev_ebitda",
        "price_to_book",
        "price_to_sales",
        "peg",
        "dividend_yield",
        "market_cap",
    ):
        if metrics.get(field) is not None:
            val_facts.append(
                {
                    "field": field,
                    "value": metrics.get(field),
                    "value_text": f"{field}={metrics.get(field)}",
                    "confidence": 0.72,
                }
            )
    if val_facts:
        objects.append(
            {
                "evidence_id": _eid("val", t, str(sorted(metrics.keys()))),
                "leo_version": "leo-v1.0.0",
                "yfp_version": YFP_VERSION,
                "evidence_type": "valuation_metrics",
                "fact_key": "valuation_snapshot",
                "value_text": "; ".join(f.get("value_text") or "" for f in val_facts)[:800],
                "value": metrics,
                "entity": t,
                "company_symbol": t,
                "source_id": "yahoo",
                "source_name": "YAHOO",
                "title": f"{t} valuation metrics (canonical)",
                "url": "",
                "published": _now(),
                "extracted_facts": val_facts[:20],
                "confidence": 0.73,
                "verification_status": "provisionally_verified",
                "rank_weight": 1.4,
                "provenance": {
                    "source_id": "yahoo",
                    "connector": "yfp",
                    "fetched_at": _now(),
                    "orchestrator": "YFP",
                },
                "metadata": {"kind": "valuation_history", "completed_by": "yfp"},
                "version": 1,
            }
        )
    return objects


def soft_update_leo_dossier(
    ticker: str,
    evidence_objects: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Append evidence into LEO dossier via existing update_dossier (no redesign)."""
    if not evidence_objects:
        return {"updated": False, "reason": "no_objects"}
    try:
        from leo.dossier import update_dossier

        dossier = update_dossier(
            ticker,
            evidence_objects,
            plan={
                "ticker": (ticker or "").upper(),
                "intent": "valuation",
                "required_evidence": ["financial_statements", "valuation_metrics", "market_data"],
                "source": "yfp",
            },
        )
        return {
            "updated": True,
            "ticker": (ticker or "").upper(),
            "objects": len(evidence_objects),
            "dossier_keys": list((dossier or {}).keys())[:20],
        }
    except Exception as exc:  # noqa: BLE001
        return {"updated": False, "error": str(exc)[:200]}
