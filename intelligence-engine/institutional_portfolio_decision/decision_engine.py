"""CIO-01 decision engine — portfolio decisions reference company decisions."""

from __future__ import annotations

import hashlib
from typing import Any, Optional, Sequence

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_portfolio_decision.allocation_actions import generate_allocation_actions
from institutional_portfolio_decision.calibration import calibrate_portfolio
from institutional_portfolio_decision.exposure_actions import generate_exposure_actions
from institutional_portfolio_decision.models import (
    CompanyDecisionRef,
    InstitutionalPortfolioDecision,
)
from institutional_portfolio_decision.monitoring import build_monitoring_plan, monitoring_items_flat
from institutional_portfolio_decision.schema import (
    DECISION_ENGINE_VERSION,
    LINEAGE_CHAIN,
    VALIDATOR_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _decision_id(portfolio_id: str, version: int, recommendation: str) -> str:
    raw = f"{portfolio_id}|{version}|{recommendation}|{DECISION_ENGINE_VERSION}"
    return f"cio-{portfolio_id.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def build_company_decision_refs(
    portfolio: InstitutionalPortfolio,
) -> tuple[tuple[CompanyDecisionRef, ...], tuple[CompanyDecisionRef, ...]]:
    """
    Map holdings to referential company decision links.

    Company recommendations are inputs — never rewritten here.
    """
    supporting: list[CompanyDecisionRef] = []
    contradicting: list[CompanyDecisionRef] = []
    # Dominant recommendation by weight
    weights = {"BUY": 0.0, "HOLD": 0.0, "SELL": 0.0}
    for h in portfolio.holdings:
        rec = (h.recommendation or "HOLD").upper()
        if rec not in weights:
            rec = "HOLD"
        weights[rec] = weights.get(rec, 0.0) + float(h.weight)
    dominant = max(weights, key=weights.get) if portfolio.holdings else "HOLD"

    for h in portfolio.holdings:
        rec = (h.recommendation or "HOLD").upper()
        if rec not in {"BUY", "HOLD", "SELL"}:
            rec = "HOLD"
        role = "supporting" if rec == dominant else "contradicting"
        ref = CompanyDecisionRef(
            ticker=h.ticker,
            decision_id=h.decision_id,
            recommendation=rec,
            confidence=int(h.confidence or 0),
            conviction="",
            weight=float(h.weight),
            role=role,
        )
        if role == "contradicting":
            contradicting.append(ref)
        else:
            supporting.append(ref)
    return tuple(supporting), tuple(contradicting)


def _recommendation_from_policy(policy_summary: dict[str, Any]) -> Optional[tuple[str, str, str]]:
    """Map PCE-01 primary violation to a portfolio recommendation."""
    if not policy_summary or not policy_summary.get("has_breach"):
        return None
    primary = policy_summary.get("primary_violation") or {}
    cid = str(primary.get("constraint_id") or "")
    name = str(primary.get("name") or "Policy Constraint")
    reason = f"policy:{cid or 'breach'}:{name.replace(' ', '_').lower()}"

    if cid in {"pos_max_holding", "pos_max_top5", "div_max_hhi", "div_max_sector"}:
        return ("Reduce Concentration", "Defensive", reason)
    if cid == "sec_max_it":
        return ("Reduce Technology", "Defensive", reason)
    if cid in {"sec_max_financials", "sec_max_energy", "div_min_holdings"}:
        return ("Increase Diversification", "Defensive", reason)
    if cid == "cash_min":
        return ("Increase Cash", "Defensive", reason)
    if cid in {"risk_max_stress", "risk_max_beta", "liq_max_illiquid", "liq_max_exit_days", "cash_max"}:
        return ("Review Portfolio", "Review", reason)
    return ("Reduce Concentration", "Defensive", reason)


def _choose_recommendation(
    *,
    sector_concentration: float,
    hhi: float,
    cash_weight: float,
    top_sector: str,
    allocation_delta_cash: float,
    has_trim_actions: bool,
    agreement: float,
    sell_weight: float,
    policy_summary: Optional[dict[str, Any]] = None,
) -> tuple[str, str, str]:
    """Return (recommendation, posture, rule_path). Policy breaches outrank heuristic risk rules."""
    policy_rec = _recommendation_from_policy(dict(policy_summary or {}))
    if policy_rec is not None:
        return policy_rec

    # Priority rules — first match wins
    if sector_concentration >= 0.85 or hhi >= 0.28:
        return (
            "Reduce Concentration",
            "Defensive",
            "rule:concentration_critical",
        )
    if sector_concentration >= 0.70 and has_trim_actions:
        if top_sector.lower() in {"banking", "financials", "banks", "finance"}:
            return (
                "Increase Diversification",
                "Defensive",
                "rule:sector_concentration_financials",
            )
        if "tech" in top_sector.lower() or top_sector.lower() in {"information technology", "it"}:
            return (
                "Reduce Technology",
                "Defensive",
                "rule:sector_concentration_technology",
            )
        return (
            "Increase Diversification",
            "Defensive",
            "rule:sector_concentration",
        )
    if allocation_delta_cash > 0 or (cash_weight < 0.06 and sector_concentration >= 0.60):
        return (
            "Increase Cash",
            "Defensive",
            "rule:cash_buffer",
        )
    if sell_weight >= 0.20:
        return (
            "Review Portfolio",
            "Review",
            "rule:sell_weight_material",
        )
    if (
        top_sector.lower() in {"banking", "financials", "banks", "finance"}
        and agreement >= 0.75
        and sector_concentration < 0.70
        and hhi < 0.20
    ):
        return (
            "Increase Financials",
            "Constructive",
            "rule:financials_constructive",
        )
    if agreement >= 0.8 and hhi < 0.22 and sector_concentration < 0.75:
        return (
            "Maintain Allocation",
            "Neutral",
            "rule:maintain_stable",
        )
    if not has_trim_actions and agreement >= 0.6:
        return (
            "No Action Required",
            "Neutral",
            "rule:no_material_change",
        )
    return (
        "Maintain Allocation",
        "Neutral",
        "rule:default_maintain",
    )


def generate_portfolio_decision(
    portfolio: InstitutionalPortfolio,
    *,
    previous_version: int = 0,
    concentration: Optional[dict[str, Any]] = None,
    portfolio_risk: Any = None,
    policy_assessment: Any = None,
    observation_health: float = 0.7,
    forecast_stability: float = 0.7,
) -> InstitutionalPortfolioDecision:
    """
    Build an InstitutionalPortfolioDecision from portfolio + PRE-01 risk + PCE-01 policy + company refs.

    Risk and policy are authoritative inputs. Company decisions are referential only.
    """
    risk_summary: dict[str, Any] = {}
    portfolio_risk_id = ""
    overall_risk = ""
    if portfolio_risk is not None:
        try:
            from institutional_portfolio_risk.risk_engine import risk_summary_for_cio

            risk_summary = risk_summary_for_cio(portfolio_risk)
            portfolio_risk_id = str(getattr(portfolio_risk, "risk_id", "") or "")
            overall_risk = str(getattr(portfolio_risk, "overall_risk", "") or "")
            hhi = float(risk_summary.get("hhi") or 0.0)
            sector_concentration = float(risk_summary.get("sector_concentration") or 0.0)
            top_sector = str(risk_summary.get("top_sector") or "")
        except Exception:  # noqa: BLE001
            portfolio_risk = None

    if portfolio_risk is None:
        conc = dict(concentration or {})
        hhi = float(conc.get("hhi") or 0.0)
        sectors = [e for e in portfolio.exposures if e.dimension == "sector"]
        sector_concentration = float(sectors[0].weight) if sectors else 0.0
        top_sector = sectors[0].name if sectors else ""

    policy_summary: dict[str, Any] = {}
    policy_id = ""
    policy_status = ""
    if policy_assessment is not None:
        try:
            from institutional_policy.policy_engine import policy_summary_for_cio

            policy_summary = policy_summary_for_cio(policy_assessment)
            policy_id = str(getattr(policy_assessment, "policy_id", "") or "")
            policy_status = str(getattr(policy_assessment, "overall_status", "") or "")
        except Exception:  # noqa: BLE001
            policy_assessment = None
            policy_summary = {}

    supporting, contradicting = build_company_decision_refs(portfolio)
    all_refs = tuple(list(supporting) + list(contradicting))
    sell_weight = sum(r.weight for r in all_refs if r.recommendation == "SELL")
    agreement = 0.0
    if all_refs:
        buckets: dict[str, float] = {}
        for r in all_refs:
            buckets[r.recommendation] = buckets.get(r.recommendation, 0.0) + r.weight
        agreement = max(buckets.values()) if buckets else 0.0

    alloc_actions = generate_allocation_actions(
        portfolio,
        refs=all_refs,
        sector_concentration=sector_concentration,
        hhi=hhi,
    )
    cash_delta = 0.0
    for a in alloc_actions:
        if a.ticker == "CASH":
            cash_delta = a.to_weight - a.from_weight
    has_trim = any(a.to_weight < a.from_weight and a.ticker != "CASH" for a in alloc_actions)

    recommendation, posture, rule_path = _choose_recommendation(
        sector_concentration=sector_concentration,
        hhi=hhi,
        cash_weight=float(portfolio.cash_weight or 0.0),
        top_sector=top_sector,
        allocation_delta_cash=cash_delta,
        has_trim_actions=has_trim,
        agreement=agreement,
        sell_weight=sell_weight,
        policy_summary=policy_summary,
    )

    # Special-case label when banking book constructive increase
    if recommendation == "Increase Diversification" and top_sector.lower() in {
        "banking",
        "financials",
        "banks",
    }:
        # Keep Increase Diversification — more accurate than Increase Financials when already concentrated
        pass

    exposure_actions = generate_exposure_actions(portfolio)
    calibration, scorecard = calibrate_portfolio(
        portfolio,
        refs=all_refs,
        hhi=hhi,
        sector_concentration=sector_concentration,
        recommendation=recommendation,
        observation_health=observation_health,
        forecast_stability=forecast_stability,
    )
    plan = build_monitoring_plan(
        portfolio,
        refs=all_refs,
        allocation_actions=alloc_actions,
        recommendation=recommendation,
        sector_concentration=sector_concentration,
    )
    version = int(previous_version or 0) + 1
    # Prefer PRE-01 stress/warnings as portfolio_risks when available
    if portfolio_risk is not None and getattr(portfolio_risk, "stress_results", None):
        risks = tuple(
            {
                "kind": "stress",
                "label": s.label,
                "severity": s.severity,
                "score": float(s.portfolio_impact_pct),
                "detail": s.detail,
                "source": "PRE-01",
            }
            for s in portfolio_risk.stress_results
        )
    else:
        risks = tuple(r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in portfolio.risks)

    lineage = (
        "Portfolio",
        "Holding",
        "Portfolio Risk",
        "Policy Constraint",
        "Company Decision",
        "Reason",
        "Evidence",
    ) if (portfolio_risk_id or policy_id) else LINEAGE_CHAIN

    return InstitutionalPortfolioDecision(
        portfolio_id=portfolio.portfolio_id,
        decision_id=_decision_id(portfolio.portfolio_id, version, recommendation),
        decision_version=version,
        generated_at=now_iso(),
        recommendation=recommendation,
        confidence=calibration.confidence,
        conviction=calibration.conviction,
        investment_posture=posture,
        supporting_decisions=supporting,
        contradicting_decisions=contradicting,
        allocation_actions=alloc_actions,
        exposure_actions=exposure_actions,
        portfolio_risks=risks,
        monitoring_items=monitoring_items_flat(plan),
        monitoring_plan=plan,
        calibration=calibration,
        scorecard=scorecard,
        diagnostics=None,
        lineage=lineage,
        portfolio_graph_id=portfolio.graph_id,
        portfolio_risk_id=portfolio_risk_id,
        overall_risk=overall_risk,
        portfolio_risk_summary=risk_summary or None,
        policy_id=policy_id,
        policy_status=policy_status,
        policy_summary=policy_summary or None,
        decision_engine_version=DECISION_ENGINE_VERSION,
        validator_version=VALIDATOR_VERSION,
        rule_path=rule_path,
        llm=False,
        mutates_company_decisions=False,
        consumes_pre01=bool(portfolio_risk_id),
        consumes_pce01=bool(policy_id),
    )
