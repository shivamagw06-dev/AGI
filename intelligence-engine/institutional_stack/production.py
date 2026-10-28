"""Institutional Intelligence Stack production facade — soft integration only."""

from __future__ import annotations

from html import escape
from typing import Any

from institutional_stack.flags import flags_dict, is_enabled
from institutional_stack.pipeline import (
    bootstrap,
    company_pack,
    ensure_filings_seeded,
    ingest_and_refresh,
    refresh_ticker,
)
from institutional_stack.schema import (
    ARCHITECTURE_STATUS,
    DEFAULT_BOOTSTRAP_TICKERS,
    LAYERS,
    PIPELINE,
    PROGRAMME,
    PROGRAMME_SHORT,
    STACK_VERSION,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": STACK_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "orchestration_only": True,
        "pipeline": list(PIPELINE),
        "layers": list(LAYERS),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "fil",
            "fdi",
            "mii",
            "eil",
            "pil",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "certification",
            "regression",
        ],
    }


def dashboard() -> dict[str, Any]:
    seed = ensure_filings_seeded()
    layer_health: dict[str, Any] = {}
    for key, mod in (
        ("filing_intelligence", "filing_intelligence.production"),
        ("filing_diff", "filing_diff.production"),
        ("management_intelligence", "management_intelligence.production"),
        ("accounting_intelligence", "accounting_intelligence.production"),
        ("portfolio_intelligence", "portfolio_intelligence.production"),
        ("peer_intelligence", "peer_intelligence.production"),
        ("causal_intelligence", "causal_graph.production"),
        ("forecast_intelligence", "forecast_intelligence.production"),
        ("knowledge_graph", "knowledge_graph.production"),
        ("institutional_memory", "institutional_memory.production"),
        ("simulation_lab", "simulation_lab.production"),
        ("decision_engine_v2", "decision_engine_v2.production"),
        ("evidence_intelligence", "academy.evidence.production"),
    ):
        try:
            import importlib

            m = importlib.import_module(mod)
            if hasattr(m, "dashboard"):
                d = m.dashboard()
                layer_health[key] = {
                    "enabled": d.get("enabled", True),
                    "version": d.get("version")
                    or d.get("mii_version")
                    or d.get("fil_version")
                    or d.get("fdi_version")
                    or d.get("pil_version")
                    or d.get("cig_version")
                    or d.get("fie_version")
                    or d.get("ikg_version")
                    or d.get("ilm_version")
                    or d.get("ssl_version")
                    or d.get("idev2_version")
                    or d.get("eil_version"),
                    "primary_question": d.get("primary_question"),
                }
            else:
                layer_health[key] = {"enabled": True}
        except Exception as exc:
            layer_health[key] = {"enabled": False, "error": str(exc)[:120]}

    sample = company_pack("HDFCBANK", analyst="committee")
    return {
        "programme": PROGRAMME,
        "version": STACK_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "pipeline": list(PIPELINE),
        "layers": list(LAYERS),
        "seed": seed,
        "layer_health": layer_health,
        "sample_ticker": "HDFCBANK",
        "sample_summary": sample.get("summary"),
        "bootstrap_tickers": list(DEFAULT_BOOTSTRAP_TICKERS),
        "website_surfaces": [
            "/admin/institutional-stack",
            "/admin/filing-intelligence",
            "/admin/filing-diff",
            "/admin/management-intelligence",
            "/admin/accounting-intelligence",
            "/admin/portfolio-intelligence",
            "/admin/causal-intelligence",
            "/admin/forecast-intelligence",
            "/admin/knowledge-graph",
            "/admin/institutional-memory",
            "/admin/simulation-lab",
            "/admin/decision-engine-v2",
            "/admin/peer-intelligence",
        ],
        "api_prefix": "/v1/institutional-stack",
    }


def company(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    return company_pack(ticker, analyst=analyst)


def analyse(ticker: str) -> dict[str, Any]:
    ensure_filings_seeded()
    chain = refresh_ticker(ticker)
    pack = company_pack(ticker, analyst="committee")
    return {"enabled": is_enabled(), "chain": chain, **pack}


def ingest(payload: dict[str, Any]) -> dict[str, Any]:
    return ingest_and_refresh(payload)


def bootstrap_stack(tickers: list[str] | None = None) -> dict[str, Any]:
    return bootstrap(tickers)


def soft_slice_for_ask_agi(ticker: str | None) -> dict[str, Any]:
    if not is_enabled() or not ticker:
        return {}
    pack = company_pack(ticker, analyst="committee")
    return {
        "institutional_stack": {
            "enabled": True,
            "version": STACK_VERSION,
            "ticker": pack.get("ticker"),
            "summary": pack.get("summary"),
            "layers": pack.get("layers"),
            "pipeline": pack.get("pipeline"),
            "rule": "FIL→FDI→MII→ACI→EIL→PIL→CIG→IKG→FIE→ILM→SSL→IDE_V2 soft facts precede CIO judgement",
        }
    }


def soft_slice_for_company_analysis(ticker: str | None) -> dict[str, Any]:
    return soft_slice_for_ask_agi(ticker)


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    pack = company_pack(ticker, analyst=analyst)
    return {"institutional_stack": pack}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    d = dashboard()
    return {
        "institutional_stack": {
            "enabled": True,
            "version": STACK_VERSION,
            "pipeline": list(PIPELINE),
            "layers_healthy": sum(
                1 for v in (d.get("layer_health") or {}).values() if v.get("enabled") is not False
            ),
            "seed_documents": (d.get("seed") or {}).get("document_count"),
            "sample_summary": d.get("sample_summary"),
            "quality_gates_passed": quality_gates().get("passed"),
        }
    }


def soft_slice_for_mission_control() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    seed = ensure_filings_seeded()
    pack = company_pack("HDFCBANK")
    layers = pack.get("layers") or {}
    checks = {
        "enabled": is_enabled(),
        "filings_seeded": bool(seed.get("seeded")) and int(seed.get("document_count") or 0) >= 1,
        "fil_present": bool(layers.get("filing_intelligence")),
        "fdi_present": bool(layers.get("filing_diff")),
        "mii_present": bool(layers.get("management_intelligence")),
        "aci_present": bool(layers.get("accounting_intelligence")),
        "pio_present": bool(layers.get("portfolio_intelligence")),
        "cig_present": bool(layers.get("causal_intelligence")),
        "fie_present": bool(layers.get("forecast_intelligence")),
        "ikg_present": bool(layers.get("knowledge_graph")),
        "ilm_present": bool(layers.get("institutional_memory")),
        "ssl_present": bool(layers.get("simulation_lab")),
        "idev2_present": bool(layers.get("decision_engine_v2")),
        "pil_present": bool(layers.get("peer_intelligence")),
        "eil_present": bool(layers.get("evidence_intelligence")),
        "mii_confidence": (layers.get("management_intelligence") or {}).get("confidence") is not None,
        "aci_confidence": (layers.get("accounting_intelligence") or {}).get("confidence") is not None,
        "cig_upstream": bool((layers.get("causal_intelligence") or {}).get("upstream_drivers")),
        "fie_most_likely": (layers.get("forecast_intelligence") or {}).get("most_likely") is not None,
        "ikg_relationships": (layers.get("knowledge_graph") or {}).get("relationship_count") is not None,
        "ilm_lessons": (layers.get("institutional_memory") or {}).get("lesson_count") is not None,
        "ssl_expected_return": (layers.get("simulation_lab") or {}).get("expected_return") is not None,
        "idev2_gate": (layers.get("decision_engine_v2") or {}).get("recommendation_status") is not None,
        "no_engine_redesign": True,
        "architecture_frozen": True,
    }
    return {
        "programme": PROGRAMME,
        "version": STACK_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "flags": flags_dict(),
    }


def admin_page() -> str:
    d = dashboard()
    qg = quality_gates()
    sample = d.get("sample_summary") or {}
    rows = "".join(
        f"<tr><td>{escape(k)}</td><td>{escape(str((v or {}).get('enabled')))}</td>"
        f"<td>{escape(str((v or {}).get('version') or '—'))}</td>"
        f"<td>{escape(str((v or {}).get('primary_question') or '—')[:120])}</td></tr>"
        for k, v in (d.get("layer_health") or {}).items()
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>Institutional Intelligence Stack</title>
<style>
body{{font-family:ui-sans-serif,system-ui;margin:2rem;background:#0b1220;color:#e8eef8}}
h1{{font-size:1.4rem}} .muted{{color:#9bb0c9}} table{{border-collapse:collapse;width:100%;margin-top:1rem}}
td,th{{border:1px solid #243247;padding:.5rem .75rem;text-align:left;font-size:.9rem}}
.ok{{color:#4ade80}} .bad{{color:#fbbf24}} .card{{background:#121a2b;border:1px solid #243247;border-radius:12px;padding:1rem;margin:1rem 0}}
</style></head><body>
<p class="muted">AGIB · {escape(PROGRAMME_SHORT)} · {escape(STACK_VERSION)} · Architecture {escape(ARCHITECTURE_STATUS)}</p>
<h1>Institutional Intelligence Stack</h1>
<p>Soft integration of FIL → FDI → MII → EIL → PIL into analysts, Ask AGI, Mission Control and the website. Not a new engine.</p>
<div class="card">
  <p>Seed documents: <strong>{escape(str((d.get('seed') or {}).get('document_count')))}</strong></p>
  <p>Quality gates: <span class="{'ok' if qg.get('passed') else 'bad'}">{'PASS' if qg.get('passed') else 'REVIEW'}</span></p>
  <p>HDFC sample — MII confidence {escape(str(sample.get('management_confidence')))} · DNA {escape(str(sample.get('management_dna')))}</p>
</div>
<table><thead><tr><th>Layer</th><th>Enabled</th><th>Version</th><th>Primary question</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="muted">Pipeline: {" → ".join(escape(p) for p in PIPELINE)}</p>
</body></html>"""
