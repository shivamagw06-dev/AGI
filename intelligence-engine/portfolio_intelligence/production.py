"""PIO production facade — soft institutional layer, no redesign."""

from __future__ import annotations

from typing import Any

from portfolio_intelligence.flags import flags_dict, is_enabled
from portfolio_intelligence.pipeline import analyse_portfolio
from portfolio_intelligence.portfolio.packs import default_portfolio_id, list_portfolios
from portfolio_intelligence.schema import PIO_VERSION


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_PORTFOLIO_INTELLIGENCE_OFFICE",
        "version": PIO_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Does this company improve this specific portfolio?",
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "never_buy_sell": True,
        "does_not_replace_company_analysis": True,
        "not_an_engine_redesign": True,
    }


def strategy_execution_gate(strategy_id: str) -> dict[str, Any]:
    """Fail-closed bridge from strategy validation into portfolio construction."""
    from strategy_lab.production import REGISTRY
    from strategy_lab.registry_store import load_latest_evidence
    from strategy_lab.validation_registry import evaluate

    key = str(strategy_id or "").strip().lower()
    if key not in REGISTRY:
        return {"ok": False, "strategy_id": key, "execution_eligible": False,
                "decision": "BLOCKED", "reason": "UNKNOWN_STRATEGY"}
    evidence = load_latest_evidence(force=True).get(key, {})
    decision = evaluate(
        key,
        requested_lifecycle="PRODUCTION",
        evidence=evidence,
        health="HEALTHY",
        allowed_use="Portfolio construction only after independent production approval",
    )
    allowed = decision.get("execution") == "ALLOWED" and decision.get("lifecycle") == "PRODUCTION"
    return {
        "ok": True,
        "strategy_id": key,
        "strategy_name": REGISTRY[key]["name"],
        "execution_eligible": allowed,
        "decision": "ALLOWED" if allowed else "BLOCKED",
        "supported_lifecycle": decision.get("supported_lifecycle"),
        "failed_gates": decision.get("failed_gates") or [],
        "missing_gates": decision.get("missing_gates") or [],
        "validation_registry": decision,
        "rule": "Research output cannot size or alter a portfolio unless the Validation Registry permits execution.",
    }


def dashboard() -> dict[str, Any]:
    sample = analyse_portfolio(default_portfolio_id(), candidate="KOTAKBANK")
    return {
        "programme": "AGIB_PORTFOLIO_INTELLIGENCE_OFFICE",
        "pio_version": PIO_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Does this company improve this specific portfolio?",
        "flags": flags_dict(),
        "portfolios": list_portfolios(),
        "default_portfolio": default_portfolio_id(),
        "sample_health": (sample.get("health") or {}).get("grade") if sample.get("found") else None,
        "sample_pqe": (sample.get("portfolio_quality") or {}).get("portfolio_quality"),
        "pipeline": [
            "Official Filings",
            "FIL",
            "FDI",
            "MII",
            "ACI",
            "EIL",
            "PIL",
            "Institutional Analysts",
            "Investment Committee",
            "PORTFOLIO INTELLIGENCE OFFICE",
            "CIO",
            "Research Writer",
            "ACS",
            "IRS",
            "Production",
        ],
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "filing_intelligence",
            "filing_diff",
            "management_intelligence",
            "accounting_intelligence",
            "evidence_intelligence",
            "peer_intelligence",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "certification",
            "regression",
            "institutional_stack",
        ],
    }


def portfolio(portfolio_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "pio_version": PIO_VERSION}
    out = analyse_portfolio(portfolio_id)
    return {"enabled": True, **out}


def analyse(
    portfolio_id: str | None = None,
    *,
    candidate: str | None = None,
    candidate_weight: float | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "pio_version": PIO_VERSION}
    out = analyse_portfolio(portfolio_id, candidate=candidate, candidate_weight=candidate_weight)
    return {"enabled": True, **out}


def portfolio_health(portfolio_id: str) -> dict[str, Any]:
    out = analyse_portfolio(portfolio_id)
    return {
        "enabled": is_enabled(),
        "pio_version": PIO_VERSION,
        "portfolio_id": out.get("portfolio_id") or portfolio_id,
        "found": out.get("found"),
        "health": out.get("health"),
        "portfolio_quality": out.get("portfolio_quality"),
        "confidence": out.get("confidence"),
    }


def scenarios(portfolio_id: str) -> dict[str, Any]:
    out = analyse_portfolio(portfolio_id)
    return {
        "enabled": is_enabled(),
        "pio_version": PIO_VERSION,
        "portfolio_id": out.get("portfolio_id") or portfolio_id,
        "found": out.get("found"),
        "scenarios": out.get("scenarios"),
    }


def soft_slice_for_analyst(
    ticker: str,
    *,
    analyst: str = "committee",
    portfolio_id: str | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_portfolio(portfolio_id or default_portfolio_id(), candidate=ticker)
    if not out.get("found"):
        return {"portfolio_intelligence": {"enabled": True, "found": False}}
    report = out.get("report") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "version": PIO_VERSION,
        "portfolio_id": out["portfolio_id"],
        "candidate": ticker.upper(),
        "health_grade": (out.get("health") or {}).get("grade"),
        "portfolio_quality": (out.get("portfolio_quality") or {}).get("portfolio_quality"),
        "suitability": out.get("suitability"),
        "impact": out.get("impact"),
        "rule": "Ask whether this investment improves this portfolio — not whether the stock is good in isolation",
        "never_recommendation": True,
    }
    if analyst in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
    elif analyst == "research_writer":
        base["writer_blocks"] = {
            "narrative": report.get("executive_summary"),
            "tables": {
                "sector_exposure": out.get("allocation"),
                "factor_exposure": out.get("factors"),
                "scenarios": (out.get("scenarios") or {}).get("scenarios"),
                "risk_contributions": (out.get("risk") or {}).get("contributions"),
                "pqe": out.get("portfolio_quality"),
            },
        }
    elif analyst == "financial":
        base["desk"] = {
            "risk": out.get("risk"),
            "liquidity": out.get("liquidity"),
            "impact": out.get("impact"),
        }
    elif analyst == "business":
        base["desk"] = {
            "portfolio_quality": out.get("portfolio_quality"),
            "suitability": out.get("suitability"),
        }
    return {"portfolio_intelligence": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "portfolio_intelligence": {
            "enabled": True,
            "version": PIO_VERSION,
            "portfolios": len(list_portfolios()),
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Portfolio analysis never replaces company analysis; no investment recommendation",
        }
    }


def quality_gates() -> dict[str, Any]:
    out = analyse_portfolio(default_portfolio_id(), candidate="KOTAKBANK")
    report = out.get("report") or {}
    text = (report.get("text") or "").lower()
    checks = {
        "enabled": is_enabled(),
        "portfolio_found": bool(out.get("found")),
        "never_replaces_company_analysis": bool(out.get("does_not_replace_company_analysis")),
        "candidate_in_portfolio_context": bool(out.get("candidate") and out.get("impact")),
        "diversification_calculated": (out.get("diversification") or {}).get("diversification") is not None,
        "concentration_calculated": (out.get("concentration") or {}).get("concentration") is not None,
        "risk_budget_calculated": (out.get("risk") or {}).get("expected_volatility") is not None,
        "scenario_analysis_completed": len(((out.get("scenarios") or {}).get("scenarios") or [])) >= 5,
        "pqe_scored": (out.get("portfolio_quality") or {}).get("portfolio_quality") is not None,
        "no_investment_recommendation": ("buy now" not in text and "sell now" not in text and bool(out.get("never_recommendation"))),
        "evidence_backed": (out.get("evidence") or {}).get("count", 0) >= 1,
        "flags": flags_dict().get("PORTFOLIO_INTELLIGENCE") is True,
    }
    return {"passed": all(checks.values()), "checks": checks, "pio_version": PIO_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    out = analyse_portfolio(default_portfolio_id(), candidate="KOTAKBANK")
    health_b = out.get("health") or {}
    pqe = out.get("portfolio_quality") or {}
    suit = out.get("suitability") or {}
    impact = out.get("impact") or {}
    return f"""<!doctype html>
<html><head><title>PIO — Portfolio Intelligence Office</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Portfolio Intelligence Office</h1>
<p>Primary question: <em>Does this company improve this specific portfolio?</em></p>
<div class="card">
  <div>Version: {dash.get('pio_version')}</div>
  <div>Portfolios: {', '.join(dash.get('portfolios') or [])}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>{(out.get('profile') or {}).get('name')}</h2>
  <div>Grade <strong>{health_b.get('grade')}</strong> · Overall {health_b.get('overall')} · PQE <strong>{pqe.get('portfolio_quality')}</strong></div>
  <div>Candidate KOTAKBANK → net effect <strong>{impact.get('net_portfolio_effect')}</strong></div>
  <div>Suitability: {suit.get('summary')}</div>
  <p>{(out.get('report') or {}).get('cio_brief')}</p>
</div>
<p>API: /v1/portfolio-intelligence/* · Flag: PORTFOLIO_INTELLIGENCE · Never Buy/Sell</p>
</body></html>"""
