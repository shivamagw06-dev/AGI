"""UX interrogation API — expose Evidence Pack / DJG / PDG / OG / Learning Graph.

Read-only soft-wire surfaces for product UX. Never mutates production overlays.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.fundamentals.universe import coverage_for, tier_report
from institutional_reasoning.institutional_evidence.production import package_for_governance as ie_pack
from institutional_reasoning.ipi.decision import decide_portfolio
from institutional_reasoning.observability import snapshot as obs_snapshot

INTERROGATE_VERSION = "intelligence-interrogate-v1.0.0"


def evidence_pack(ticker: str) -> dict[str, Any]:
    pkg = ie_pack(ticker)
    pack = pkg.get("institutional_evidence") or {}
    return {
        "interrogate_version": INTERROGATE_VERSION,
        "kind": "evidence_pack",
        "ticker": str(ticker).upper(),
        "found": bool(pkg.get("found")),
        "validated_fields": list((pack.get("validated") or {}).keys()),
        "summary": pack.get("summary"),
        "modules": list((pack.get("modules") or {}).keys()),
        "risk_drivers": pack.get("risk_drivers"),
        "downside_case": pack.get("downside_case"),
        "coverage": pack.get("coverage"),
        "evidence_score": pack.get("evidence_score"),
        "derivation_note": "Ratios are derived from primitives; risk from return series.",
        "pack": pack,
    }


def decision_graphs(question: str, *, ticker: str | None = None) -> dict[str, Any]:
    record = govern_answer(question, ticker_hint=ticker)
    return {
        "interrogate_version": INTERROGATE_VERSION,
        "kind": "decision_graphs",
        "question": question,
        "question_type": record.get("question_type"),
        "entity": record.get("entity"),
        "djg": record.get("justification_graph"),
        "pdg": record.get("portfolio_decision_graph"),
        "outcome_graph": (record.get("ioi") or {}).get("outcome_graph")
        or record.get("outcome_graph"),
        "learning_graph": (record.get("cal") or {}).get("learning_graph")
        or record.get("learning_graph"),
        "validation": record.get("validation"),
        "committee": record.get("committee"),
        "ipi": {
            "action": ((record.get("ipi") or {}).get("committee") or {}).get("action"),
            "withheld": (record.get("ipi") or {}).get("withheld"),
            "target_weight": ((record.get("ipi") or {}).get("sizing") or {}).get("target_weight"),
        }
        if record.get("ipi")
        else None,
    }


def portfolio_view(ticker: str) -> dict[str, Any]:
    decision = decide_portfolio(entity_id=ticker, persist_memory=False)
    return {
        "interrogate_version": INTERROGATE_VERSION,
        "kind": "portfolio_view",
        "ticker": str(ticker).upper(),
        "decision": {
            "action": (decision.get("committee") or {}).get("action"),
            "withheld": decision.get("withheld"),
            "target_weight": (decision.get("sizing") or {}).get("target_weight"),
            "risk_drivers": (decision.get("risk") or {}).get("risk_drivers"),
            "provider": (decision.get("risk") or {}).get("provider"),
        },
        "pdg": decision.get("portfolio_decision_graph"),
        "coverage": coverage_for(ticker),
    }


def stack_surface(*, ticker: str = "INFY", tier: str = "nifty_50") -> dict[str, Any]:
    return {
        "interrogate_version": INTERROGATE_VERSION,
        "evidence": evidence_pack(ticker),
        "portfolio": portfolio_view(ticker),
        "universe": tier_report(tier),
        "observability": obs_snapshot(),
    }
