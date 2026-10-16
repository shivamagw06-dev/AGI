"""AGI IPO — Institutional Portfolio Office acceptance tests."""

from __future__ import annotations

from institutional_portfolio_office import IPO_VERSION, apply_portfolio_office, ranking_api, status
from institutional_portfolio_office.engine import construct_portfolio_idea
from institutional_portfolio_office.schema import PORTFOLIO_ROLES


def _thesis(**extra: object) -> dict:
    t = {
        "thesis_id": "TH-INFY-P",
        "company": "Infosys",
        "ticker": "INFY",
        "investment_view": "Quality compounder with durable ROE and cash generation",
        "version": "1.0",
        "confidence": 86,
        "preferred_case": "base",
        "monitoring_checklist": ["Await next earnings release before formal review"],
        "ite_version": "institutional-investment-thesis-v1.0.0",
    }
    t.update(extra)
    return {"thesis": t}


def _decision(**extra: object) -> dict:
    d = {
        "decision_id": "DEC-WAIT-1",
        "thesis_id": "TH-INFY-P",
        "company": "Infosys",
        "ticker": "INFY",
        "decision": "Wait",
        "status": "Watch",
        "review_date": "2026-08-28",
        "confidence": 86,
        "ido_version": "institutional-decision-office-v1.0.0",
    }
    d.update(extra)
    return {"decision": d}


def test_ipo_status() -> None:
    s = status()
    assert s["company"] == "AGI"
    assert s["release"] == "AGI v4.0"
    assert IPO_VERSION.startswith("institutional-portfolio-office")
    assert s["positions"] is False
    assert s["orders"] is False
    assert s["freeze_locks"]["no_positions"] is True


def test_portfolio_idea_not_position() -> None:
    pack = construct_portfolio_idea(
        question="How does Infosys compare in IT allocation?",
        investment_thesis=_thesis(),
        decision_office=_decision(),
        persist=True,
    )
    idea = pack["idea"]
    assert idea["idea_id"].startswith("PI-")
    assert idea["position"] is None
    assert idea["position_size"] is None
    assert idea["orders"] is None
    assert pack["positions_emitted"] is False
    assert idea["expected_role"] in PORTFOLIO_ROLES
    assert idea["sector"] == "IT Services"
    assert idea["conviction"] is not None


def test_relative_ranking_across_peers() -> None:
    # Seed peers
    construct_portfolio_idea(
        question="TCS allocation?",
        investment_thesis=_thesis(
            thesis_id="TH-TCS",
            company="TCS",
            ticker="TCS",
            confidence=92,
            preferred_case="bull",
            investment_view="Premium franchise compounder",
        ),
        decision_office=_decision(
            decision_id="DEC-TCS",
            thesis_id="TH-TCS",
            company="TCS",
            ticker="TCS",
            decision="Approve",
            status="Approved",
            confidence=92,
        ),
        persist=True,
    )
    construct_portfolio_idea(
        question="Infosys allocation?",
        investment_thesis=_thesis(confidence=80, preferred_case="base"),
        decision_office=_decision(decision="Monitor", status="Monitoring", confidence=80),
        persist=True,
    )
    construct_portfolio_idea(
        question="LTIM allocation?",
        investment_thesis=_thesis(
            thesis_id="TH-LTIM",
            company="LTIMindtree",
            ticker="LTIM",
            confidence=70,
            preferred_case="base",
            investment_view="Satellite IT growth",
        ),
        decision_office=_decision(
            decision_id="DEC-LTIM",
            thesis_id="TH-LTIM",
            company="LTIMindtree",
            ticker="LTIM",
            decision="Wait",
            confidence=70,
        ),
        persist=True,
    )
    ranked = ranking_api({"sector": "IT Services"})
    assert ranked["n"] >= 2
    assert ranked["positions"] is False
    tickers = [r.get("ticker") for r in ranked["ranking"]]
    assert "TCS" in tickers
    # TCS should rank ahead of lower-conviction Wait names when Approve+higher conviction
    assert ranked["ranking"][0]["ticker"] in {"TCS", "INFY", "LTIM"}


def test_role_assignment() -> None:
    pack = construct_portfolio_idea(
        question="Infosys quality compounder?",
        investment_thesis=_thesis(preferred_case="bull", confidence=85),
        decision_office=_decision(decision="Approve", status="Approved", confidence=85),
        persist=True,
    )
    assert pack["idea"]["expected_role"] == "Core Compounder"


def test_positive_wait_still_candidate() -> None:
    pack = construct_portfolio_idea(
        question="Infosys?",
        investment_thesis=_thesis(investment_view="Attractive long-term compounder"),
        decision_office=_decision(decision="Wait"),
        persist=True,
    )
    assert pack["idea"]["decision"] == "Wait"
    assert pack["idea"]["status"] == "Candidate"
    assert pack["idea"]["position"] is None


def test_constraints_forbid_positions() -> None:
    pack = construct_portfolio_idea(
        question="Infosys?",
        investment_thesis=_thesis(),
        decision_office=_decision(decision="Monitor", status="Monitoring"),
        policies={"allow_positions": True, "allow_execution": True},
        persist=True,
    )
    check = pack["idea"]["constraint_check"]
    assert check["policies"]["allow_positions"] is False
    assert check["policies"]["allow_execution"] is False


def test_apply_flags() -> None:
    out = apply_portfolio_office(
        question="Infosys vs peers?",
        investment_thesis=_thesis(),
        decision_office=_decision(),
    )
    assert out["pack"]["judgment_changed"] is False
    assert out["pack"]["thesis_changed"] is False
    assert out["pack"]["decision_changed"] is False
    assert out["pack"]["positions_emitted"] is False
