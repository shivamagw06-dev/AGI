"""FIL production facade — soft layer, no engine redesign."""

from __future__ import annotations

from typing import Any

from filing_intelligence.flags import flags_dict, is_enabled
from filing_intelligence.ingestion.store import all_documents, documents_for, ingest_document, reset_for_tests
from filing_intelligence.peer_sync import live_panel_for, soft_slice_for_pil
from filing_intelligence.pipeline import analyse_ticker
from filing_intelligence.schema import FIL_VERSION, FilingDocument


def dashboard() -> dict[str, Any]:
    docs = all_documents()
    fdi_slice: dict[str, Any] = {}
    try:
        from filing_diff.production import soft_slice_for_fil

        fdi_slice = soft_slice_for_fil()
    except Exception as exc:
        fdi_slice = {"filing_diff": {"enabled": False, "soft_error": str(exc)}}
    return {
        "programme": "AGIB_FILING_INTELLIGENCE_LAYER",
        "fil_version": FIL_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "What do the company's own filings actually say?",
        "flags": flags_dict(),
        "document_count": len(docs),
        "tickers": sorted({d.get("ticker") for d in docs}),
        "pipeline": [
            "Official Filings",
            "Filing Intelligence Layer",
            "Filing Diff Engine",
            "Evidence Intelligence Layer",
            "Peer Intelligence Layer",
            "Institutional Analysts",
            "Investment Committee",
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
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "academy",
            "certification",
            "regression",
            "peer_intelligence",
        ],
        **fdi_slice,
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "fil_version": FIL_VERSION}
    out = analyse_ticker(ticker)
    return {"enabled": True, "fil_version": FIL_VERSION, **out}


def history(ticker: str) -> dict[str, Any]:
    out = analyse_ticker(ticker)
    return {
        "enabled": is_enabled(),
        "fil_version": FIL_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "history": out.get("history"),
        "origin": "filing_intelligence",
    }


def timeline(ticker: str) -> dict[str, Any]:
    out = analyse_ticker(ticker)
    return {
        "enabled": is_enabled(),
        "fil_version": FIL_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "timeline": out.get("timeline") or [],
    }


def evidence(ticker: str) -> dict[str, Any]:
    out = analyse_ticker(ticker)
    return {
        "enabled": is_enabled(),
        "fil_version": FIL_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "evidence": out.get("evidence"),
        "confidence": out.get("confidence"),
    }


def analyse(ticker: str) -> dict[str, Any]:
    return company(ticker)


def ingest(payload: dict[str, Any]) -> dict[str, Any]:
    doc = FilingDocument(
        doc_id=str(payload["doc_id"]),
        ticker=str(payload["ticker"]).upper(),
        company=str(payload.get("company") or payload["ticker"]),
        doc_type=str(payload.get("doc_type") or "regulatory_filing"),
        title=str(payload.get("title") or ""),
        period=str(payload.get("period") or ""),
        as_of=str(payload.get("as_of") or ""),
        url=str(payload.get("url") or ""),
        evidence_tier=int(payload.get("evidence_tier") or 1),
        source_publisher=str(payload.get("source_publisher") or ""),
        text=str(payload.get("text") or ""),
        tables=list(payload.get("tables") or []),
        metadata=dict(payload.get("metadata") or {}),
    )
    result = ingest_document(doc)
    if result.get("accepted"):
        # peer refresh signal
        result["peer_refresh"] = live_panel_for(doc.ticker)
        # Soft auto-chain FDI → MII (no FIL/FDI/MII redesign)
        if not payload.get("skip_stack_chain"):
            try:
                from institutional_stack.flags import is_enabled as stack_enabled
                from institutional_stack.pipeline import refresh_ticker

                if stack_enabled():
                    result["institutional_stack_chain"] = refresh_ticker(doc.ticker)
            except Exception as exc:
                result["institutional_stack_chain"] = {"ok": False, "error": str(exc)[:160]}
    return result


def soft_slice_for_analyst(ticker: str, *, analyst: str = "general") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_ticker(ticker)
    if not out.get("found"):
        return {"filing_intelligence": {"enabled": True, "found": False, "ticker": ticker}}
    focus = {
        "business": ["management", "segments", "narrative"],
        "financial": ["history", "notes", "capital_allocation"],
        "valuation": ["history", "guidance_tracker", "capital_allocation"],
        "risk": ["risk_register", "management"],
        "committee": ["timeline", "guidance_tracker", "capital_allocation", "narrative"],
        "cio": ["narrative", "confidence", "timeline"],
        "research_writer": ["timeline", "management", "capital_allocation", "history"],
    }.get(analyst, ["narrative", "history", "evidence"])
    slice_: dict[str, Any] = {
        "enabled": True,
        "version": FIL_VERSION,
        "ticker": out["ticker"],
        "rule": "Historical financial trends must originate from validated filing intelligence when available",
    }
    for key in focus:
        slice_[key] = out.get(key)
    return {"filing_intelligence": slice_}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "filing_intelligence": {
            "enabled": True,
            "version": FIL_VERSION,
            "document_count": len(all_documents()),
            "rule": "Every company conclusion supported by filing evidence whenever available",
            "quality_gates_passed": quality_gates().get("passed"),
        }
    }


def soft_slice_for_eil() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "filing_intelligence": {
            "enabled": True,
            "version": FIL_VERSION,
            "role": "Tier-1/2 company filing facts for EIL claim support",
        }
    }


def quality_gates() -> dict[str, Any]:
    hdfc = analyse_ticker("HDFCBANK")
    nestle = analyse_ticker("NESTLEIND")
    axis = analyse_ticker("AXISBANK")
    # peer sync refresh check
    from filing_intelligence.peer_sync import overlay_peer_series
    from peer_intelligence.peer_database.packs.banks_india import pack as banks_pack

    synced = overlay_peer_series(banks_pack())
    live_metrics = [
        s for s in synced.get("series") or []
        if s.get("entity") == "HDFCBANK" and s.get("data_class") == "live_filing"
    ]
    narrative = (hdfc.get("narrative") or "").lower()
    checks = {
        "enabled": is_enabled(),
        "hdfc_found": bool(hdfc.get("found")),
        "hdfc_has_cet1": any(f.get("metric") == "CET1" for f in hdfc.get("facts") or []),
        "hdfc_timeline": len(hdfc.get("timeline") or []) >= 2,
        "hdfc_narrative_filing_origin": "filing intelligence" in narrative or "cet1" in narrative,
        "nestle_found": bool(nestle.get("found")),
        "axis_nim": any(f.get("metric") == "NIM" for f in axis.get("facts") or []),
        "evidence_tiers_present": (hdfc.get("evidence") or {}).get("count", 0) >= 5,
        "peer_sync_live_filing": len(live_metrics) >= 1,
        "append_only_docs": len(documents_for("HDFCBANK")) >= 3,
        "flags": flags_dict().get("FILING_INTELLIGENCE") is True,
    }
    return {"passed": all(checks.values()), "checks": checks, "fil_version": FIL_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    hdfc = analyse_ticker("HDFCBANK")
    docs = hdfc.get("documents") or []
    rows = "".join(
        f"<tr><td>{d.get('as_of')}</td><td>{d.get('doc_type')}</td>"
        f"<td>{d.get('period')}</td><td>{d.get('title')}</td>"
        f"<td>T{d.get('evidence_tier')}</td></tr>"
        for d in docs
    )
    return f"""<!doctype html>
<html><head><title>FIL — Filing Intelligence</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a3440;padding:.4rem;text-align:left}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Filing Intelligence Layer</h1>
<p>Primary question: <em>What do the company's own filings actually say?</em></p>
<div class="card">
  <div>Version: {dash.get('fil_version')}</div>
  <div>Documents: {dash.get('document_count')}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFC filing timeline</h2>
<table><tr><th>Date</th><th>Type</th><th>Period</th><th>Title</th><th>Tier</th></tr>{rows}</table>
</div>
<div class="card"><h2>Narrative</h2>
<p>{hdfc.get('narrative')}</p>
<p><strong>Confidence:</strong> {(hdfc.get('confidence') or {}).get('explain')}</p>
</div>
<p>API: /v1/filing-intelligence/* · Flag: FILING_INTELLIGENCE</p>
</body></html>"""


__all__ = [
    "admin_page",
    "analyse",
    "company",
    "dashboard",
    "evidence",
    "history",
    "ingest",
    "quality_gates",
    "reset_for_tests",
    "soft_slice_for_analyst",
    "soft_slice_for_eil",
    "soft_slice_for_irs",
    "soft_slice_for_pil",
    "timeline",
]
