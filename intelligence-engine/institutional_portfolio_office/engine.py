"""Deterministic Institutional Portfolio Office.

Relative thinking over Portfolio Ideas — not positions, not orders, not execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from institutional_portfolio_office import store as idea_store
from institutional_portfolio_office.schema import (
    DEFAULT_POLICIES,
    FREEZE_LOCKS,
    IDEA_SCHEMA_VERSION,
    IPO_VERSION,
    OWNER,
    PEER_UNIVERSES,
    PORTFOLIO_ROLES,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bump_version(prev: dict[str, Any] | None) -> str:
    if not prev:
        return "1.0"
    ver = str(prev.get("version") or "1.0")
    try:
        major, minor = ver.split(".", 1)
        return f"{int(major)}.{int(minor) + 1}"
    except Exception:
        return "1.1"


def _thesis(pack: dict[str, Any] | None) -> dict[str, Any]:
    p = pack or {}
    return dict(p.get("thesis") or p)


def _decision(pack: dict[str, Any] | None) -> dict[str, Any]:
    p = pack or {}
    return dict(p.get("decision") or p)


def _infer_sector(company: str | None, ticker: str | None, question: str) -> str:
    blob = f"{company or ''} {ticker or ''} {question}".lower()
    if any(x in blob for x in ("infosys", "infy", "tcs", "ltim", "wipro", "hcl", "persistent", "it services")):
        return "IT Services"
    if any(x in blob for x in ("hdfc", "icici", "kotak", "axis", "bank")):
        return "Private Banks"
    if any(x in blob for x in ("reliance", "ongc", "bpcl", "energy", "oil")):
        return "Energy"
    return "Diversified"


def _infer_theme(sector: str, role: str) -> str:
    if sector == "IT Services":
        return "India IT compounders"
    if sector == "Private Banks":
        return "India private bank franchise"
    if sector == "Energy":
        return "India energy complex"
    return f"{sector} — {role}"


def _assign_role(thesis: dict[str, Any], decision: dict[str, Any]) -> str:
    view = str(thesis.get("investment_view") or "").lower()
    preferred = str(thesis.get("preferred_case") or decision.get("committee_preferred_case") or "").lower()
    dec = str(decision.get("decision") or "")
    if "turnaround" in view or "restructur" in view:
        return "Turnaround"
    if "event" in view or "merger" in view or dec.startswith("Review After"):
        return "Event Driven"
    if "defensive" in view or "dividend" in view or "income" in view:
        return "Income" if "dividend" in view or "income" in view else "Defensive"
    if "cyclical" in view or preferred == "bear":
        return "Cyclical" if "cyclical" in view else "Satellite"
    if preferred == "bull" and float(thesis.get("confidence") or 0) >= 80:
        return "Core Compounder"
    if "compounder" in view or "franchise" in view or "roe" in view:
        return "Core Compounder"
    if dec in {"Wait", "Increase Research"}:
        return "Satellite"
    if dec == "Monitor":
        return "Core Compounder" if "quality" in view else "Satellite"
    return "Satellite"


def _conviction(thesis: dict[str, Any], decision: dict[str, Any]) -> float:
    try:
        conf = float(thesis.get("confidence") if thesis.get("confidence") is not None else decision.get("confidence") or 50)
    except (TypeError, ValueError):
        conf = 50.0
    dec = str(decision.get("decision") or "")
    boost = {
        "Approve": 8.0,
        "Monitor": 4.0,
        "Review After Earnings": 2.0,
        "Review After Budget": 1.0,
        "Review After Results": 1.0,
        "Wait": -5.0,
        "Increase Research": -8.0,
        "Escalate": -12.0,
        "Reject": -25.0,
    }.get(dec, 0.0)
    preferred = str(thesis.get("preferred_case") or "").lower()
    if preferred == "bull":
        boost += 3.0
    elif preferred == "bear":
        boost -= 4.0
    return round(max(0.0, min(100.0, conf + boost)), 2)


def _idea_status(decision: dict[str, Any]) -> str:
    dec = str(decision.get("decision") or "")
    if dec == "Reject":
        return "Rejected"
    if dec in {"Approve", "Monitor"}:
        return "Active Consideration"
    if dec in {"Wait", "Increase Research", "Escalate"} or dec.startswith("Review After"):
        return "Candidate"
    return "Candidate"


def _correlation_note(sector: str, role: str) -> str:
    if sector == "IT Services":
        return "High peer correlation within India IT; differentiate via franchise quality and valuation timing"
    if sector == "Private Banks":
        return "Elevated sector beta to rates/credit; role differentiation matters"
    if role == "Macro Hedge":
        return "Intended low correlation to risk assets"
    return "Correlation assessed qualitatively vs sector peers — not a position hedge"


def _check_policies(
    *,
    sector: str,
    theme: str,
    ticker: str | None,
    status: str,
    policies: dict[str, Any],
) -> dict[str, Any]:
    peers = idea_store.list_ideas(sector=sector, limit=200)
    active = [p for p in peers if p.get("status") == "Active Consideration"]
    sector_n = max(1, len(peers))
    sector_share = round(100.0 * len(active) / sector_n, 2) if peers else 0.0
    same_ticker = [
        p
        for p in active
        if ticker and str(p.get("ticker") or "").upper() == ticker.upper()
    ]
    violations = []
    if policies.get("allow_positions"):
        violations.append("policy_allows_positions_forbidden_in_ipo_v1")
    if policies.get("allow_execution"):
        violations.append("policy_allows_execution_forbidden_in_ipo_v1")
    if len(same_ticker) > int(policies.get("max_single_name_ideas") or 1):
        violations.append("single_name_concentration")
    if sector_share > float(policies.get("max_sector_share_pct") or 35.0) and status == "Active Consideration":
        violations.append("sector_concentration")
    theme_n = len(idea_store.list_ideas(theme=theme, limit=200))
    if theme_n > int(policies.get("max_theme_ideas") or 12):
        violations.append("theme_capacity")
    return {
        "compliant": len(violations) == 0,
        "violations": violations,
        "sector_active_share_pct": sector_share,
        "n_sector_ideas": len(peers),
        "n_theme_ideas": theme_n,
        "policies": {
            "max_single_name_ideas": policies.get("max_single_name_ideas"),
            "max_sector_share_pct": policies.get("max_sector_share_pct"),
            "allow_positions": False,
            "allow_execution": False,
        },
    }


def _peer_ranking_table(sector: str, ticker: str | None, relative_rank: int | None) -> list[dict[str, Any]]:
    """Combine stored ideas with illustrative peer universe labels for CIO-style lists."""
    stored = idea_store.ideas_in_sector(sector)
    by_ticker = {
        str(x.get("ticker") or x.get("company") or "").upper(): x
        for x in stored
        if x.get("status") in {"Candidate", "Active Consideration"}
    }
    universe = list(PEER_UNIVERSES.get(sector) or ())
    # Ensure current ticker in universe label list
    if ticker and ticker.upper() not in universe:
        universe = list(universe) + [ticker.upper()]
    rows = []
    # Prefer live conviction ranks from store; fill gaps with universe order
    live = sorted(
        [x for x in stored if x.get("status") in {"Candidate", "Active Consideration"}],
        key=lambda x: (int(x.get("relative_rank") or 999), -float(x.get("conviction") or 0)),
    )
    if live:
        for i, idea in enumerate(live, start=1):
            rows.append(
                {
                    "rank": i,
                    "ticker": idea.get("ticker") or idea.get("company"),
                    "company": idea.get("company"),
                    "conviction": idea.get("conviction"),
                    "expected_role": idea.get("expected_role"),
                    "source": "portfolio_idea",
                }
            )
        return rows
    # Fallback illustrative ordering when store empty for sector
    for i, t in enumerate(universe, start=1):
        rows.append(
            {
                "rank": i,
                "ticker": t,
                "company": t,
                "conviction": None,
                "expected_role": None,
                "source": "illustrative_universe",
                "note": "Illustrative peer slate — not a holding list",
            }
        )
    if ticker and relative_rank:
        # annotate
        for r in rows:
            if str(r.get("ticker") or "").upper() == ticker.upper():
                r["is_subject"] = True
    return rows


def construct_portfolio_idea(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
    policies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thesis = _thesis(investment_thesis)
    decision = _decision(decision_office)
    pol = {**DEFAULT_POLICIES, **(policies or {})}
    pol["allow_positions"] = False
    pol["allow_execution"] = False

    company = thesis.get("company") or decision.get("company") or "Unspecified Company"
    ticker = thesis.get("ticker") or decision.get("ticker")
    sector = _infer_sector(str(company), str(ticker) if ticker else None, question)
    role = _assign_role(thesis, decision)
    if role not in PORTFOLIO_ROLES:
        role = "Satellite"
    theme = _infer_theme(sector, role)
    conviction = _conviction(thesis, decision)
    status = _idea_status(decision)

    idea_id = idea_store.make_idea_id(str(ticker or company), theme)
    prev = idea_store.get(idea_id)
    is_update = bool(prev)
    version = _bump_version(prev) if is_update else "1.0"

    idea = {
        "idea_id": idea_id,
        "company": company,
        "ticker": ticker,
        "sector": sector,
        "theme": theme,
        "investment_thesis_id": thesis.get("thesis_id"),
        "investment_thesis_version": thesis.get("version"),
        "investment_view": thesis.get("investment_view"),
        "decision_id": decision.get("decision_id"),
        "decision": decision.get("decision"),
        "decision_status": decision.get("status"),
        "relative_rank": None,
        "relative_universe_size": None,
        "conviction": conviction,
        "expected_role": role,
        "correlation": _correlation_note(sector, role),
        "risk_budget": "Unallocated — Portfolio Office tracks ideas, not capital",
        "capacity": "Idea capacity only — no position sizing in IPO v1",
        "dependencies": [
            f"thesis:{thesis.get('thesis_id')}",
            f"decision:{decision.get('decision_id')}",
            f"decision_type:{decision.get('decision')}",
        ],
        "monitoring": list(thesis.get("monitoring_checklist") or [])[:8]
        or list(decision.get("required_conditions") or [])[:4],
        "review_date": decision.get("review_date"),
        "priority": int(max(1, min(99, round(100 - conviction)))),
        "status": status,
        "position": None,
        "position_size": None,
        "orders": None,
        "execution": False,
        "owner": OWNER,
        "version": version,
        "schema_version": IDEA_SCHEMA_VERSION,
        "ipo_version": IPO_VERSION,
        "constraint_check": {},
        "peer_ranking": [],
        "question": question,
        "as_of": as_of,
        "last_updated": _utc_now(),
        "created_at": (prev or {}).get("created_at") or _utc_now(),
        "provenance": {
            "ite_version": thesis.get("ite_version") or (investment_thesis or {}).get("ite_version"),
            "ido_version": decision.get("ido_version") or (decision_office or {}).get("ido_version"),
            "icr_version": (committee_reasoning or {}).get("icr_version"),
            "icc_version": (confidence_calibration or {}).get("icc_version"),
        },
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "judgment_stack_modified": False,
        "thesis_modified": False,
        "decision_modified": False,
        "freeze_locks": dict(FREEZE_LOCKS),
        "metadata": dict(metadata or {}),
    }

    pack = {
        "ipo_version": IPO_VERSION,
        "schema_version": IDEA_SCHEMA_VERSION,
        "idea": idea,
        "idea_id": idea_id,
        "persisted": False,
        "guides_portfolio": True,
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
        "thesis_changed": False,
        "decision_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }

    if persist:
        saved = idea_store.upsert(idea, is_update=is_update)
        # Re-rank sector after upsert
        idea_store.recompute_relative_ranks(sector)
        refreshed = idea_store.get(idea_id) or saved
        refreshed["constraint_check"] = _check_policies(
            sector=sector,
            theme=theme,
            ticker=str(ticker) if ticker else None,
            status=str(refreshed.get("status") or status),
            policies=pol,
        )
        refreshed["peer_ranking"] = _peer_ranking_table(
            sector, str(ticker) if ticker else None, refreshed.get("relative_rank")
        )
        # persist enrichment
        saved2 = idea_store.upsert(refreshed, is_update=True)
        pack["idea"] = saved2
        pack["persisted"] = True
        pack["peer_ranking"] = saved2.get("peer_ranking")
        pack["relative_rank"] = saved2.get("relative_rank")

    return pack
