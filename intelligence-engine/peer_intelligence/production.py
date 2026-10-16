"""PIL production facade — soft layer, no engine redesign."""

from __future__ import annotations

from typing import Any

from peer_intelligence.benchmarking.engine import benchmarks_for
from peer_intelligence.commentary.engine import commentary_for
from peer_intelligence.evidence.attach import evidence_bundle
from peer_intelligence.flags import flags_dict, is_enabled
from peer_intelligence.historical.series import history_for
from peer_intelligence.peer_database.store import list_packs
from peer_intelligence.percentile.engine import percentiles_for
from peer_intelligence.rankings.engine import rankings_for
from peer_intelligence.reports.build import build_report
from peer_intelligence.resolver.resolve import resolve_peers
from peer_intelligence.schema import PIL_VERSION
from peer_intelligence.scorecards.build import scorecard
from peer_intelligence.visualization.charts import visualization_pack


def dashboard() -> dict[str, Any]:
    filing_slice: dict[str, Any] = {}
    try:
        from filing_intelligence.peer_sync import soft_slice_for_pil

        filing_slice = soft_slice_for_pil()
    except Exception as exc:
        filing_slice = {"filing_intelligence": {"enabled": False, "soft_error": str(exc)}}
    return {
        "programme": "AGIB_PEER_INTELLIGENCE_LAYER",
        "pil_version": PIL_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "How does this company compare to the best and most relevant peers?",
        "flags": flags_dict(),
        "packs": list_packs(),
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "academy",
            "certification",
            "regression",
        ],
        **filing_slice,
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "pil_version": PIL_VERSION}
    card = scorecard(ticker)
    return {
        "enabled": True,
        "pil_version": PIL_VERSION,
        "resolve": resolve_peers(ticker),
        "scorecard": card,
        "percentiles": percentiles_for(ticker),
        "rankings": rankings_for(ticker),
        "history": history_for(ticker),
        "commentary": commentary_for(ticker),
        "evidence": evidence_bundle(ticker),
        "visualization": visualization_pack(ticker),
    }


def compare(tickers: list[str], *, metric: str | None = None) -> dict[str, Any]:
    rows = []
    for t in tickers:
        pct = percentiles_for(t)
        if metric:
            hit = next((p for p in pct.get("percentiles") or [] if p["metric"] == metric), None)
            rows.append({"ticker": pct.get("ticker") or t, "metric": metric, "row": hit})
        else:
            rows.append(
                {
                    "ticker": pct.get("ticker") or t,
                    "top": (pct.get("percentiles") or [])[:5],
                }
            )
    return {"enabled": is_enabled(), "pil_version": PIL_VERSION, "compare": rows, "metric": metric}


def analyse(ticker: str, *, focus_metrics: list[str] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False}
    return {
        "enabled": True,
        "pil_version": PIL_VERSION,
        "benchmarks": benchmarks_for(ticker),
        "commentary": commentary_for(ticker, focus_metrics=focus_metrics),
        "report": build_report(ticker),
        "scorecard": scorecard(ticker),
    }


def history(ticker: str, metric: str | None = None) -> dict[str, Any]:
    return {"enabled": is_enabled(), "pil_version": PIL_VERSION, **history_for(ticker, metric)}


def rankings(ticker: str | None = None, *, sector: str | None = None) -> dict[str, Any]:
    if ticker:
        return {"enabled": is_enabled(), "pil_version": PIL_VERSION, **rankings_for(ticker)}
    # sector league table from packs
    from peer_intelligence.peer_database.packs import all_packs

    tables = []
    for p in all_packs():
        if sector and p["sector"] != sector:
            continue
        subject = (p.get("direct_universe") or [None])[0]
        if subject:
            tables.append(rankings_for(subject))
    return {"enabled": is_enabled(), "pil_version": PIL_VERSION, "tables": tables}


def soft_slice_for_analyst(ticker: str, *, analyst: str = "general") -> dict[str, Any]:
    """Additive slice for BA/FA/VA/Risk/Sector/Macro/Committee/CIO/RW."""
    if not is_enabled():
        return {}
    card = scorecard(ticker)
    if not card.get("found"):
        return {"peer_intelligence": {"enabled": True, "found": False, "ticker": ticker}}
    dims = card.get("ranking_summary") or {}
    focus_map = {
        "business": ["business_quality", "funding"],
        "financial": ["financial_quality", "returns", "margins", "capital"],
        "valuation": ["valuation", "returns"],
        "risk": ["asset_quality", "capital"],
        "sector": ["business_quality", "growth"],
        "macro": ["funding", "growth"],
        "committee": list(dims.keys()),
        "cio": list(dims.keys()),
        "research_writer": list(dims.keys()),
    }
    keys = focus_map.get(analyst, list(dims.keys())[:3])
    return {
        "peer_intelligence": {
            "enabled": True,
            "version": PIL_VERSION,
            "ticker": card["ticker"],
            "sector": card.get("sector"),
            "ranking_summary": {k: dims[k] for k in keys if k in dims},
            "narrative": card.get("narrative"),
            "trajectory_insight": card.get("trajectory_insight"),
            "outliers": card.get("outliers") or [],
            "confidence": card.get("confidence"),
            "rule": "Reference peer / history / sector ranking before judgement",
        }
    }


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "peer_intelligence": {
            "enabled": True,
            "version": PIL_VERSION,
            "packs": len(list_packs()),
            "rule": "No generic standalone conclusions where peer evidence exists",
            "quality_gates_passed": quality_gates().get("passed"),
        }
    }


def soft_slice_for_eil() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "peer_intelligence": {
            "enabled": True,
            "version": PIL_VERSION,
            "role": "Populate peer/history pillars that EIL marks as gaps",
        }
    }


def quality_gates() -> dict[str, Any]:
    hdfc = analyse("HDFCBANK")
    nestle = commentary_for("NESTLEIND")
    tcs = rankings_for("TCS")
    eternal = resolve_peers("ETERNAL")
    narrative = (hdfc.get("commentary") or {}).get("narrative") or ""
    checks = {
        "enabled": is_enabled(),
        "banks_pack": any(p["pack_id"] == "banks_india_v1" for p in list_packs()),
        "fmcg_pack": any(p["pack_id"] == "fmcg_india_v1" for p in list_packs()),
        "it_pack": any(p["pack_id"] == "it_services_v1" for p in list_packs()),
        "consumer_pack": any(p["pack_id"] == "consumer_internet_v1" for p in list_packs()),
        "hdfc_resolved": bool((hdfc.get("scorecard") or {}).get("found")),
        "hdfc_narrative_relative": "rank" in narrative.lower() or "percentile" in narrative.lower(),
        "hdfc_trajectory": bool((hdfc.get("commentary") or {}).get("trajectory_insight")),
        "nestle_relative": "rank" in ((nestle.get("narrative") or "").lower()),
        "tcs_ranks": bool(tcs.get("metric_ranks")),
        "eternal_peers": bool(eternal.get("resolved")),
        "flags_present": flags_dict().get("PEER_INTELLIGENCE") is True,
    }
    return {"passed": all(checks.values()), "checks": checks, "pil_version": PIL_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    packs = dash.get("packs") or []
    rows = "".join(
        f"<tr><td>{p['pack_id']}</td><td>{p['sector']}</td>"
        f"<td>{', '.join(p.get('direct_universe') or [])}</td>"
        f"<td>{p.get('series_count')}</td></tr>"
        for p in packs
    )
    hdfc = commentary_for("HDFCBANK")
    return f"""<!doctype html>
<html><head><title>PIL — Peer Intelligence</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Peer Intelligence Layer</h1>
<p>Primary question: <em>How does this company compare to the best and most relevant peers?</em></p>
<div class="card">
  <div>Version: {dash.get('pil_version')}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>Peer packs</h2>
<table><tr><th>Pack</th><th>Sector</th><th>Direct universe</th><th>Series</th></tr>{rows}</table>
</div>
<div class="card"><h2>HDFC sample narrative</h2>
<p>{hdfc.get('narrative')}</p>
<p><strong>Trajectory:</strong> {hdfc.get('trajectory_insight')}</p>
</div>
<p>API: /v1/peer-intelligence/* · Flags: PEER_INTELLIGENCE</p>
</body></html>"""
