"""SSL production facade — soft institutional layer, no redesign."""

from __future__ import annotations

from typing import Any

from simulation_lab.flags import flags_dict, is_enabled
from simulation_lab.pipeline import (
    run_portfolio_simulation,
    run_simulation,
    scenarios_pack,
    simulation_history,
)
from simulation_lab.schema import (
    ARCHITECTURE_STATUS,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PRIMARY_QUESTION_ALT,
    PROGRAMME,
    PROGRAMME_SHORT,
    SSL_VERSION,
)
from simulation_lab.store.corpus import catalogue_meta


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": SSL_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "primary_question_alt": PRIMARY_QUESTION_ALT,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "active_experimentation": True,
        "not_analysis_only": True,
        "no_unsupported_deterministic_outcomes": True,
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }


def dashboard() -> dict[str, Any]:
    sample = run_simulation({"scenario_id": "rebalance_hdfc_plus"}) if is_enabled() else {}
    return {
        "programme": PROGRAMME,
        "ssl_version": SSL_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "catalogue": catalogue_meta(),
        "sample_scenario": "rebalance_hdfc_plus",
        "sample_expected_return": (sample.get("probabilities") or {}).get("expected_return"),
        "sample_confidence": (sample.get("confidence") or {}).get("confidence"),
        "sample_summary": (sample.get("report") or {}).get("executive_summary"),
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/simulation-lab"],
        "api_prefix": "/v1/simulation",
    }


def scenarios() -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ssl_version": SSL_VERSION}
    return {"enabled": True, **scenarios_pack()}


def run(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ssl_version": SSL_VERSION}
    out = run_simulation(payload or {})
    return {"enabled": True, **out}


def portfolio(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ssl_version": SSL_VERSION}
    out = run_portfolio_simulation(payload or {})
    return {"enabled": True, **out}


def history(*, limit: int = 50) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "ssl_version": SSL_VERSION}
    return {"enabled": True, **simulation_history(limit=limit)}


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    t = (ticker or "HDFCBANK").upper()
    # Prefer ticker-linked scenario
    scenario_id = {
        "HDFCBANK": "rebalance_hdfc_plus",
        "TCS": "trim_tcs_growth",
        "NESTLEIND": "oil_plus_20_nestle",
    }.get(t, "rebalance_hdfc_plus")
    out = run_simulation({"scenario_id": scenario_id, "ticker": t})
    report = out.get("report") or {}
    decision = out.get("decision") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": SSL_VERSION,
        "ticker": t,
        "primary_question": PRIMARY_QUESTION,
        "scenario_id": scenario_id,
        "expected_return": (out.get("probabilities") or {}).get("expected_return"),
        "expected_volatility": (out.get("probabilities") or {}).get("expected_volatility"),
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "opportunity_cost_analysed": bool((out.get("opportunity_cost") or {}).get("analysed")),
        "stress_completed": bool((out.get("stress") or {}).get("completed")),
        "summary": report.get("executive_summary"),
        "rule": "Experiment before allocate — probabilistic simulation, not a trade ticket",
        "never_recommendation": True,
        "active_experimentation": True,
    }
    role = (analyst or "committee").lower()
    if role in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["decision_package"] = decision
        base["alternative_strategies"] = (out.get("strategies") or {}).get("strategies")
        base["monitoring_plan"] = decision.get("recommended_monitoring")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
    elif role in {"financial", "business", "risk", "macro", "sector", "valuation"}:
        base["desk"] = {
            "distribution": (out.get("probabilities") or {}).get("distribution"),
            "sensitivity": out.get("sensitivity"),
            "macro": out.get("macro"),
            "portfolio_impact": report.get("portfolio_changes"),
        }
    else:
        base["desk"] = {"summary": base["summary"]}
    base["portfolio_office"] = report.get("portfolio_office")
    return {"simulation_lab": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "simulation_lab": {
            "enabled": True,
            "version": SSL_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Reproducible sims; explicit assumptions; distributions; stress; replay; opportunity cost; no deterministic outcomes",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    a = run_simulation({"scenario_id": "rebalance_hdfc_plus", "n": 800})
    b = run_simulation({"scenario_id": "rebalance_hdfc_plus", "n": 800})
    replay = run_simulation({"scenario_id": "replay_covid_core", "n": 600})
    checks = {
        "enabled": is_enabled(),
        "simulations_reproducible": a.get("run_key_seed") == b.get("run_key_seed")
        and (a.get("probabilities") or {}).get("bands") == (b.get("probabilities") or {}).get("bands"),
        "assumptions_explicitly_recorded": bool(a.get("assumptions_explicit"))
        and bool((a.get("scenario") or {}).get("assumptions", {}).get("explicitly_recorded")),
        "probability_distributions_generated": bool((a.get("probabilities") or {}).get("distribution"))
        and bool((a.get("probabilities") or {}).get("bands")),
        "stress_tests_completed": bool((a.get("stress") or {}).get("completed")),
        "historical_replay_available": bool((replay.get("replay") or {}).get("available")),
        "opportunity_cost_analysed": bool((a.get("opportunity_cost") or {}).get("analysed")),
        "no_unsupported_deterministic_outcomes": bool(a.get("no_unsupported_deterministic_outcomes"))
        and bool((a.get("probabilities") or {}).get("not_a_price_prediction")),
        "flags": flags_dict().get("SIMULATION_LAB") is True,
        "not_engine_redesign": bool(a.get("not_an_engine_redesign")),
        "active_experimentation_not_analysis_only": bool(a.get("active_experimentation")),
    }
    return {"passed": all(checks.values()), "checks": checks, "ssl_version": SSL_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    sample = run_simulation({"scenario_id": "rebalance_hdfc_plus", "n": 800}) if is_enabled() else {}
    dist = (sample.get("probabilities") or {}).get("distribution") or {}
    strategies = ((sample.get("strategies") or {}).get("strategies") or [])[:3]
    strat_rows = "".join(
        f"<tr><td>{s.get('label')}</td><td>{s.get('expected_return')}</td><td>{s.get('tail_risk_p05')}</td></tr>"
        for s in strategies
    )
    return f"""<!doctype html>
<html><head><title>SSL — Simulation & Strategy Lab</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Institutional Simulation & Strategy Lab</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em> — experiment before allocate.</p>
<div class="card">
  <div>Version: {dash.get('ssl_version')}</div>
  <div>Catalogue scenarios: {(dash.get('catalogue') or {}).get('scenario_count')}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>Sample — rebalance HDFCBANK</h2>
<p>{(sample.get('report') or {}).get('executive_summary')}</p>
<p>Distribution: bull {dist.get('bull')} · base {dist.get('base')} · bear {dist.get('bear')} · stress {dist.get('stress')}</p>
</div>
<div class="card"><h2>Strategy comparison</h2>
<table><thead><tr><th>Strategy</th><th>E[r]</th><th>p05</th></tr></thead>
<tbody>{strat_rows}</tbody></table>
</div>
<p>API: /v1/simulation/* · Flag: SIMULATION_LAB · Active experimentation, not analysis-only</p>
</body></html>"""
