"""FIE production facade — soft institutional layer, no redesign."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

from forecast_intelligence.flags import flags_dict, is_enabled
from forecast_intelligence.pipeline import analyse_company, analyse_query
from forecast_intelligence.profiles.packs import list_profiles
from forecast_intelligence.schema import (
    ARCHITECTURE_STATUS,
    FIE_VERSION,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PRIMARY_QUESTION_ALT,
    PROGRAMME,
    PROGRAMME_SHORT,
    SCENARIO_NAMES,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": FIE_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "primary_question_alt": PRIMARY_QUESTION_ALT,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "not_a_price_prediction": True,
        "no_deterministic_forecast": True,
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }


def dashboard() -> dict[str, Any]:
    sample = analyse_company("HDFCBANK")
    dist = ((sample.get("probabilities") or {}).get("distribution")) if sample.get("found") else {}
    return {
        "programme": PROGRAMME,
        "fie_version": FIE_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "profiles": list_profiles(),
        "scenario_names": list(SCENARIO_NAMES),
        "sample_ticker": "HDFCBANK",
        "sample_distribution": dist,
        "sample_most_likely": (sample.get("probabilities") or {}).get("most_likely") if sample.get("found") else None,
        "sample_confidence": (sample.get("confidence") or {}).get("confidence") if sample.get("found") else None,
        "sample_summary": (sample.get("report") or {}).get("executive_forecast") if sample.get("found") else None,
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/forecast-intelligence"],
        "api_prefix": "/v1/forecast",
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "fie_version": FIE_VERSION}
    out = analyse_company(ticker)
    return {"enabled": True, **out}


def scenarios(ticker: str) -> dict[str, Any]:
    out = company(ticker)
    return {
        "enabled": out.get("enabled"),
        "fie_version": FIE_VERSION,
        "ticker": out.get("ticker") or (ticker or "").upper(),
        "found": out.get("found"),
        "scenarios": out.get("scenarios"),
        "probabilities": out.get("probabilities"),
        "trigger_matrix": (out.get("triggers") or {}).get("matrix"),
        "not_a_price_prediction": True,
    }


_CATALYST_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CATALYST_CACHE_LOCK = Lock()
_CATALYST_TTL_SECONDS = 300.0


def catalysts(ticker: str) -> dict[str, Any]:
    key = (ticker or "").upper()
    now = time.monotonic()
    with _CATALYST_CACHE_LOCK:
        hit = _CATALYST_CACHE.get(key)
        if hit and now - hit[0] < _CATALYST_TTL_SECONDS:
            return hit[1]
    out = company(ticker)
    result = {
        "enabled": out.get("enabled"),
        "fie_version": FIE_VERSION,
        "ticker": out.get("ticker") or key,
        "found": out.get("found"),
        "catalysts": out.get("catalysts"),
        "not_a_price_prediction": True,
    }
    with _CATALYST_CACHE_LOCK:
        _CATALYST_CACHE[key] = (now, result)
        if len(_CATALYST_CACHE) > 200:
            oldest = min(_CATALYST_CACHE, key=lambda item: _CATALYST_CACHE[item][0])
            _CATALYST_CACHE.pop(oldest, None)
    return result


def analyse(*, ticker: str | None = None, question: str | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "fie_version": FIE_VERSION}
    out = analyse_query(ticker=ticker, question=question)
    return {"enabled": True, **out}


def soft_slice_for_analyst(
    ticker: str,
    *,
    analyst: str = "committee",
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_company(ticker)
    if not out.get("found"):
        return {"forecast_intelligence": {"enabled": True, "found": False, "ticker": (ticker or "").upper()}}
    report = out.get("report") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": FIE_VERSION,
        "ticker": out["ticker"],
        "primary_question": PRIMARY_QUESTION,
        "most_likely": (out.get("probabilities") or {}).get("most_likely"),
        "distribution": (out.get("probabilities") or {}).get("distribution"),
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "uncertainty_score": (out.get("uncertainty") or {}).get("uncertainty_score"),
        "executive_forecast": report.get("executive_forecast"),
        "rule": "Evaluate plausible futures with evidence-backed probabilities — never predict prices",
        "not_a_price_prediction": True,
        "no_deterministic_forecast": True,
        "never_recommendation": True,
    }
    role = (analyst or "committee").lower()
    if role in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["scenarios"] = out.get("scenarios")
        base["catalysts"] = (out.get("catalysts") or {}).get("timeline")
        base["portfolio_impact"] = out.get("portfolio_impact")
        base["uncertainty"] = report.get("uncertainty_assessment")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
    elif role == "macro":
        base["desk"] = {
            "sensitivity": out.get("sensitivity"),
            "catalysts": out.get("catalysts"),
            "distribution": base["distribution"],
        }
    elif role == "sector":
        base["desk"] = {
            "scenarios": out.get("scenarios"),
            "triggers": out.get("triggers"),
            "analogues": out.get("historical_analogues"),
        }
    elif role in {"financial", "valuation", "business", "risk"}:
        base["desk"] = {
            "scenarios": out.get("scenarios"),
            "expectations": out.get("expectations"),
            "portfolio_impact": out.get("portfolio_impact"),
            "uncertainty": out.get("uncertainty"),
        }
    else:
        base["desk"] = {"distribution": base["distribution"], "most_likely": base["most_likely"]}
    base["evidence"] = {
        "count": (out.get("evidence") or {}).get("count"),
        "unsupported_claims": (out.get("evidence") or {}).get("unsupported_claims"),
    }
    return {"forecast_intelligence": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "forecast_intelligence": {
            "enabled": True,
            "version": FIE_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Bull/Base/Bear with measurable triggers; evidence-backed probabilities; explicit uncertainty; no price predictions",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    out = analyse_company("HDFCBANK")
    scenarios = out.get("scenarios") or []
    names = {s.get("name") for s in scenarios}
    trig = out.get("triggers") or {}
    probs = out.get("probabilities") or {}
    cats = out.get("catalysts") or {}
    unc = out.get("uncertainty") or {}
    evid = out.get("evidence") or {}
    text = ((out.get("report") or {}).get("text") or "").lower()
    pricey = any(x in text for x in ("target price", "will hit", "price will be", "buy now", "sell now"))
    checks = {
        "enabled": is_enabled(),
        "company_found": bool(out.get("found")),
        "every_forecast_includes_bull_base_bear": {"bull", "base", "bear"}.issubset(names),
        "stress_and_recovery_present": {"stress", "recovery"}.issubset(names),
        "every_scenario_has_measurable_triggers": bool(trig.get("all_scenarios_have_triggers"))
        and bool(trig.get("all_triggers_observable")),
        "every_probability_evidence_backed": bool(probs.get("evidence_coverage"))
        and probs.get("deterministic") is False
        and (evid.get("count") or 0) >= 1,
        "every_catalyst_linked_to_evidence": all(
            c.get("linked_to_evidence") for c in (cats.get("items") or [])
        )
        and (cats.get("count") or 0) >= 1,
        "every_uncertainty_explicitly_disclosed": bool(unc.get("explicitly_disclosed"))
        and bool(unc.get("known_unknowns"))
        and bool(unc.get("unknown_unknowns")),
        "no_unsupported_price_predictions": bool(out.get("not_a_price_prediction")) and not pricey,
        "no_deterministic_forecasts": bool(out.get("no_deterministic_forecast"))
        and probs.get("deterministic") is False
        and float((probs.get("distribution") or {}).get("base") or 0) < 1.0,
        "flags": flags_dict().get("FORECAST_INTELLIGENCE") is True,
        "not_engine_redesign": bool(out.get("not_an_engine_redesign")),
    }
    return {"passed": all(checks.values()), "checks": checks, "fie_version": FIE_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    sample = analyse_company("HDFCBANK")
    dist = (sample.get("probabilities") or {}).get("distribution") or {}
    dist_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in dist.items())
    cats = ((sample.get("catalysts") or {}).get("timeline") or [])[:8]
    cat_rows = "".join(
        f"<li>{c.get('label')} · {c.get('kind')} · {c.get('polarity')} · {c.get('horizon')}</li>" for c in cats
    )
    sens = ((sample.get("sensitivity") or {}).get("top_sensitivities") or [])[:6]
    sens_rows = "".join(
        f"<tr><td>{s.get('factor')}</td><td>{s.get('sensitivity')}</td><td>{s.get('band')}</td></tr>" for s in sens
    )
    analogues = sample.get("historical_analogues") or []
    ana_rows = "".join(
        f"<li>{a.get('year')} (sim {a.get('similarity')}): {a.get('note')}</li>" for a in analogues
    )
    return f"""<!doctype html>
<html><head><title>FIE — Forecast Intelligence</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Forecast Intelligence Engine</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em> — not a price prediction.</p>
<div class="card">
  <div>Version: {dash.get('fie_version')}</div>
  <div>Profiles: {', '.join(dash.get('profiles') or [])}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFCBANK — scenario dashboard</h2>
  <p>{(sample.get('report') or {}).get('executive_forecast')}</p>
  <table><thead><tr><th>Scenario</th><th>Probability</th></tr></thead><tbody>{dist_rows}</tbody></table>
  <p>{(sample.get('report') or {}).get('cio_brief')}</p>
</div>
<div class="card"><h2>Catalyst timeline</h2><ul>{cat_rows}</ul></div>
<div class="card"><h2>Sensitivity heatmap (top)</h2>
<table><thead><tr><th>Factor</th><th>Score</th><th>Band</th></tr></thead><tbody>{sens_rows}</tbody></table>
</div>
<div class="card"><h2>Historical analogues</h2><ul>{ana_rows}</ul></div>
<p>API: /v1/forecast/* · Flag: FORECAST_INTELLIGENCE · Probabilistic scenarios only</p>
</body></html>"""
