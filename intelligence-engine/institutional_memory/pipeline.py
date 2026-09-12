"""ILM analyse pipeline — company learning pack."""

from __future__ import annotations

from typing import Any

from institutional_memory.accuracy_engine.engine import accuracy_dashboard
from institutional_memory.analyst_memory.engine import analyst_history
from institutional_memory.committee_memory.engine import committee_history
from institutional_memory.company_memory.engine import company_timeline
from institutional_memory.confidence_history.engine import confidence_evolution
from institutional_memory.decision_journal.engine import decision_journal
from institutional_memory.evidence_history.engine import evidence_evolution
from institutional_memory.forecast_memory.engine import forecast_history
from institutional_memory.learning_engine.engine import apply_learning_update, learning_summary
from institutional_memory.management_memory.engine import management_history
from institutional_memory.mistake_intelligence.engine import mistake_summary
from institutional_memory.portfolio_memory.engine import portfolio_history
from institutional_memory.reports.build import build_report
from institutional_memory.schema import ILM_VERSION, PRIMARY_QUESTION
from institutional_memory.store.corpus import company_ids, get_company
from institutional_memory.thesis_memory.engine import thesis_history
from institutional_memory.timeline.engine import institutional_timeline


def analyse_company(ticker: str, *, portfolio_id: str = "agib_core_india") -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {
            "found": False,
            "ticker": (ticker or "").upper(),
            "ilm_version": ILM_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "available": company_ids(),
        }
    t = company["ticker"]
    pack = {
        "found": True,
        "ticker": t,
        "name": company.get("name"),
        "ilm_version": ILM_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "thesis": thesis_history(t),
        "analysts": analyst_history(t),
        "committee": committee_history(t),
        "forecasts": forecast_history(t),
        "portfolio": portfolio_history(portfolio_id),
        "company_timeline": company_timeline(t),
        "management": management_history(t),
        "decisions": decision_journal(t),
        "learning": learning_summary(t),
        "accuracy": accuracy_dashboard(t, portfolio_id=portfolio_id),
        "confidence": confidence_evolution(t),
        "evidence": evidence_evolution(t),
        "mistakes": mistake_summary(t),
        "timeline": institutional_timeline(t),
        "not_an_engine_redesign": True,
        "never_recommendation": True,
        "active_learning": True,
        "not_passive_storage": True,
    }
    pack["report"] = build_report(pack)
    return pack


def learning_update(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_learning_update(payload or {})
    ticker = (payload or {}).get("ticker")
    refreshed = analyse_company(str(ticker)) if result.get("accepted") and ticker else None
    return {
        "ilm_version": ILM_VERSION,
        "update": result,
        "company": refreshed,
        "append_only": True,
    }
