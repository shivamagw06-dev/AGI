"""CIG production facade — soft institutional layer, no redesign."""

from __future__ import annotations

from typing import Any

from causal_graph.flags import flags_dict, is_enabled
from causal_graph.graph.store import graph_snapshot
from causal_graph.pipeline import (
    analyse_company,
    analyse_event,
    analyse_query,
    heatmap,
    sector_explanation,
)
from causal_graph.propagation.engine import list_events
from causal_graph.schema import (
    ARCHITECTURE_STATUS,
    CIG_VERSION,
    NO_REDESIGN,
    PIPELINE,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": CIG_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }


def dashboard() -> dict[str, Any]:
    snap = graph_snapshot()
    sample = analyse_company("HDFCBANK")
    heat = heatmap()[:12]
    return {
        "programme": PROGRAMME,
        "cig_version": CIG_VERSION,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "node_count": snap["node_count"],
        "edge_count": snap["edge_count"],
        "sectors_modelled": snap["sectors_modelled"],
        "companies_linked": snap["companies_linked"],
        "available_events": list_events(),
        "confidence_heatmap": heat,
        "strongest_drivers": heat[:5],
        "weakest_drivers": list(reversed(heat[-5:])) if len(heat) >= 5 else heat,
        "sample_ticker": "HDFCBANK",
        "sample_summary": (sample.get("report") or {}).get("executive_summary") if sample.get("found") else None,
        "sample_confidence": (sample.get("confidence") or {}).get("confidence") if sample.get("found") else None,
        "no_redesign": list(NO_REDESIGN),
        "website_surfaces": ["/admin/causal-intelligence"],
        "api_prefix": "/v1/causal-intelligence",
    }


def graph() -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "cig_version": CIG_VERSION}
    snap = graph_snapshot()
    return {
        "enabled": True,
        "cig_version": CIG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        **snap,
        "confidence_heatmap": heatmap(snap["edges"])[:40],
        "historical_validation": True,
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "cig_version": CIG_VERSION}
    out = analyse_company(ticker)
    return {"enabled": True, **out}


def event(event_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "cig_version": CIG_VERSION}
    out = analyse_event(event_id)
    return {"enabled": True, **out}


def analyse(
    *,
    ticker: str | None = None,
    event: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "cig_version": CIG_VERSION}
    out = analyse_query(ticker=ticker, event=event, question=question)
    return {"enabled": True, **out}


def soft_slice_for_analyst(
    ticker: str,
    *,
    analyst: str = "committee",
    event: str | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_company(ticker, event=event)
    if not out.get("found"):
        return {"causal_intelligence": {"enabled": True, "found": False, "ticker": (ticker or "").upper()}}
    report = out.get("report") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "found": True,
        "version": CIG_VERSION,
        "ticker": out["ticker"],
        "primary_question": PRIMARY_QUESTION,
        "upstream_drivers": out.get("upstream_drivers"),
        "sector_model": out.get("sector_model"),
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "confidence_label": (out.get("confidence") or {}).get("label"),
        "why": report.get("why_this_happened"),
        "rule": "Explain why markets moved via evidenced causal chains — never unsupported claims",
        "never_recommendation": True,
    }
    role = (analyst or "committee").lower()
    if role in {"macro", "market"}:
        base["desk"] = {
            "macro_transmission_graph": (out.get("event") or {}).get("propagation_map"),
            "event": out.get("event"),
            "chains": out.get("chains"),
        }
    elif role == "sector":
        sec = sector_explanation(out.get("sector") or "")
        base["desk"] = {
            "sector_dependency_graph": sec,
            "sector_model": out.get("sector_model"),
            "transmission_effects": sec.get("transmission_effects") if sec.get("found") else out.get("chains"),
        }
    elif role in {"business"}:
        base["desk"] = {
            "customer_supplier_competitive": {
                "upstream_drivers": out.get("upstream_drivers"),
                "sector": out.get("sector"),
                "company_chains": out.get("primary_effects"),
            }
        }
    elif role == "financial":
        base["desk"] = {
            "financial_transmission_effects": {
                "primary": out.get("primary_effects"),
                "secondary": out.get("secondary_effects"),
                "third_order": out.get("third_order_effects"),
            }
        }
    elif role == "valuation":
        base["desk"] = {
            "discount_rate_effects": [
                c
                for c in (out.get("chains") or [])
                if any(
                    x in (c.get("path") or [])
                    for x in ("cost_of_equity", "bank_multiple", "it_multiple", "fmcg_multiple", "india_10y", "us_10y")
                )
            ][:8]
        }
    elif role == "risk":
        base["desk"] = {
            "systemic_risk_propagation": (out.get("event") or {}).get("propagation_map"),
            "portfolio_impact": out.get("portfolio_impact"),
            "transmission_risk": (out.get("portfolio_impact") or {}).get("transmission_risk"),
        }
    elif role in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["propagation_map"] = (out.get("event") or {}).get("propagation_map")
        base["counterfactuals"] = (out.get("counterfactuals") or {}).get("scenarios")
        base["portfolio_impact"] = out.get("portfolio_impact")
    elif role in {"research_writer", "writer"}:
        base["writer_blocks"] = report.get("writer_blocks")
        base["propagation_table"] = report.get("propagation_table")
    else:
        base["desk"] = {
            "chains": out.get("chains"),
            "event": {"label": (out.get("event") or {}).get("label")},
        }
    # Evidence always attached for IRS / desks
    base["evidence"] = {
        "count": (out.get("evidence") or {}).get("count"),
        "unsupported_claims": (out.get("evidence") or {}).get("unsupported_claims"),
        "rule": (out.get("evidence") or {}).get("rule"),
    }
    return {"causal_intelligence": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "causal_intelligence": {
            "enabled": True,
            "version": CIG_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Every macro/company/sector explanation uses evidenced causal chains; no unsupported claims",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    company_out = analyse_company("HDFCBANK")
    event_out = analyse_event("repo_rate_cut")
    sector_out = sector_explanation("banks")
    oil_chain = analyse_event("oil_spike")
    edges_ok = all(
        bool(e.get("evidence") or e.get("evidence_years")) and bool(e.get("validated"))
        for c in (company_out.get("chains") or [])[:5]
        for e in (c.get("edges") or [])
    )
    report_text = ((company_out.get("report") or {}).get("text") or "").lower()
    checks = {
        "enabled": is_enabled(),
        "company_found": bool(company_out.get("found")),
        "macro_explanation_uses_causal_chains": bool((event_out.get("chains") or oil_chain.get("chains"))),
        "company_explanation_identifies_upstream_drivers": bool(company_out.get("upstream_drivers")),
        "sector_explanation_includes_transmission_effects": bool(
            sector_out.get("found") and sector_out.get("transmission_effects")
        ),
        "every_causal_edge_has_evidence": edges_ok and (company_out.get("evidence") or {}).get("count", 0) >= 1,
        "no_unsupported_causal_claims": (company_out.get("evidence") or {}).get("unsupported_claims", 1) == 0,
        "primary_secondary_third_order_present": bool(event_out.get("primary_effects"))
        and bool(event_out.get("secondary_effects") or event_out.get("third_order_effects")),
        "counterfactuals_available": bool((company_out.get("counterfactuals") or {}).get("scenarios")),
        "flags": flags_dict().get("CAUSAL_INTELLIGENCE") is True,
        "no_investment_recommendation": "buy now" not in report_text and "sell now" not in report_text,
        "not_engine_redesign": bool(company_out.get("not_an_engine_redesign")),
    }
    return {"passed": all(checks.values()), "checks": checks, "cig_version": CIG_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    sample = analyse_company("HDFCBANK", event="oil_spike")
    heat = dash.get("confidence_heatmap") or []
    heat_rows = "".join(
        f"<tr><td>{h.get('source')}</td><td>{h.get('target')}</td>"
        f"<td>{h.get('strength')}</td><td>{h.get('confidence')}</td><td>{h.get('score')}</td></tr>"
        for h in heat[:15]
    )
    chains = sample.get("chains") or []
    chain_rows = "".join(
        f"<li>{' → '.join(c.get('path_labels') or [])} "
        f"(p={c.get('transmission_probability')}, {c.get('order_label')})</li>"
        for c in chains[:8]
    )
    return f"""<!doctype html>
<html><head><title>CIG — Causal Intelligence Graph</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Causal Intelligence Graph</h1>
<p>Primary question: <em>{PRIMARY_QUESTION}</em></p>
<div class="card">
  <div>Version: {dash.get('cig_version')}</div>
  <div>Nodes: {dash.get('node_count')} · Edges: {dash.get('edge_count')}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFCBANK — why did this happen?</h2>
  <p>{(sample.get('report') or {}).get('executive_summary')}</p>
  <ul>{chain_rows}</ul>
  <p>{(sample.get('report') or {}).get('cio_brief')}</p>
</div>
<div class="card"><h2>Confidence heatmap (strongest drivers)</h2>
<table><thead><tr><th>Source</th><th>Target</th><th>Strength</th><th>Confidence</th><th>Score</th></tr></thead>
<tbody>{heat_rows}</tbody></table>
</div>
<p>API: /v1/causal-intelligence/* · Flag: CAUSAL_INTELLIGENCE · Reasoning layer, not a data dump</p>
</body></html>"""
