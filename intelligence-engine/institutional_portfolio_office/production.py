"""Production façade — Institutional Portfolio Office (IPO)."""

from __future__ import annotations

from typing import Any

from institutional_portfolio_office import store as idea_store
from institutional_portfolio_office.dashboard.board import build_board
from institutional_portfolio_office.engine import construct_portfolio_idea
from institutional_portfolio_office.schema import (
    COMPANY,
    FREEZE_LOCKS,
    IDEA_SCHEMA_VERSION,
    IPO_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "version": IPO_VERSION,
        "schema_version": IDEA_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "release": "AGI v4.0",
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "IPO ranks Portfolio Ideas relatively across peers/themes/roles. "
            "Stores ideas — never positions, orders, or brokerage execution."
        ),
        "api_prefix": "/v1/portfolio",
        "observability": "langsmith_mandatory",
        "positions": False,
        "orders": False,
        "execution": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return idea_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "recent": idea_store.latest_runs(limit=limit)}


def create_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_portfolio_office(
        question=str(payload.get("question") or ""),
        investment_thesis=payload.get("investment_thesis") or {"thesis": payload.get("thesis")},
        decision_office=payload.get("decision_office") or {"decision": payload.get("decision")},
        committee_reasoning=payload.get("committee_reasoning"),
        confidence_calibration=payload.get("confidence_calibration"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
        policies=payload.get("policies"),
        persist=True,
    )
    return out.get("pack") or {}


def get_idea(idea_id: str) -> dict[str, Any]:
    doc = idea_store.get(idea_id)
    if not doc:
        return {"found": False, "idea_id": idea_id}
    return {"found": True, "idea": doc}


def list_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    rows = idea_store.list_ideas(
        sector=payload.get("sector"),
        theme=payload.get("theme"),
        role=payload.get("role"),
        status=payload.get("status"),
        company=payload.get("company"),
        limit=int(payload.get("limit") or 50),
    )
    return {"n": len(rows), "ideas": rows, "query": payload, "positions": False}


def ranking_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    sector = str(payload.get("sector") or "IT Services")
    rows = idea_store.ideas_in_sector(sector)
    ranked = [
        {
            "rank": r.get("relative_rank"),
            "ticker": r.get("ticker"),
            "company": r.get("company"),
            "conviction": r.get("conviction"),
            "expected_role": r.get("expected_role"),
            "decision": r.get("decision"),
            "status": r.get("status"),
        }
        for r in rows
        if r.get("status") in {"Candidate", "Active Consideration"}
    ]
    ranked.sort(key=lambda x: int(x.get("rank") or 999))
    return {
        "sector": sector,
        "n": len(ranked),
        "ranking": ranked,
        "note": "Relative Portfolio Idea ranking — not a holdings list",
        "positions": False,
    }


def versions_api(idea_id: str) -> dict[str, Any]:
    return {"idea_id": idea_id, "versions": idea_store.versions(idea_id)}


def apply_portfolio_office(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    policies: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IDO — consumes thesis + decision; emits PortfolioIdea."""
    pack = construct_portfolio_idea(
        question=question,
        investment_thesis=investment_thesis,
        decision_office=decision_office,
        committee_reasoning=committee_reasoning,
        confidence_calibration=confidence_calibration,
        as_of=as_of,
        metadata=metadata,
        policies=policies,
        persist=persist,
    )
    idea = pack.get("idea") or {}
    thin = {
        "ipo_version": IPO_VERSION,
        "idea_id": idea.get("idea_id"),
        "company": idea.get("company"),
        "sector": idea.get("sector"),
        "expected_role": idea.get("expected_role"),
        "relative_rank": idea.get("relative_rank"),
        "conviction": idea.get("conviction"),
        "status": idea.get("status"),
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
    }
    return {"pack": pack, "report": thin}
