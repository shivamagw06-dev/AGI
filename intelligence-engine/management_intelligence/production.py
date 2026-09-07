"""MII production facade — soft layer, no redesign."""

from __future__ import annotations

from typing import Any

from management_intelligence.flags import flags_dict, is_enabled
from management_intelligence.management_profiles.packs import list_profiles
from management_intelligence.pipeline import analyse_management
from management_intelligence.schema import MII_VERSION


def dashboard() -> dict[str, Any]:
    return {
        "programme": "AGIB_MANAGEMENT_INTELLIGENCE_ENGINE",
        "mii_version": MII_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Can this management team be trusted to compound shareholder value?",
        "flags": flags_dict(),
        "profiles": list_profiles(),
        "pipeline": [
            "Official Filings",
            "FIL",
            "FDI",
            "MII",
            "EIL",
            "PIL",
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
            "filing_intelligence",
            "filing_diff",
            "evidence_intelligence",
            "peer_intelligence",
            "company_analysis",
            "investment_committee",
            "cio",
            "research_writer",
            "certification",
            "regression",
        ],
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "mii_version": MII_VERSION}
    out = analyse_management(ticker)
    return {"enabled": True, **out}


def analyse(ticker: str) -> dict[str, Any]:
    return company(ticker)


def history(ticker: str) -> dict[str, Any]:
    out = analyse_management(ticker)
    return {
        "enabled": is_enabled(),
        "mii_version": MII_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "timeline": out.get("timeline") or [],
        "decision_journal": out.get("decision_journal") or [],
        "credibility_claims": (out.get("credibility") or {}).get("claims") or [],
    }


def guidance(ticker: str) -> dict[str, Any]:
    out = analyse_management(ticker)
    return {
        "enabled": is_enabled(),
        "mii_version": MII_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "guidance": out.get("guidance"),
    }


def soft_slice_for_analyst(ticker: str, *, analyst: str = "committee") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_management(ticker)
    if not out.get("found"):
        return {"management_intelligence": {"enabled": True, "found": False, "ticker": ticker}}
    report = out.get("report") or {}
    base = {
        "enabled": True,
        "version": MII_VERSION,
        "ticker": out["ticker"],
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "dna": (out.get("dna") or {}).get("primary"),
        "cio_brief": report.get("cio_brief"),
        "rule": "Ask whether management can be trusted — not what they said",
    }
    if analyst == "business":
        base["desk"] = {
            "leadership": out.get("leadership"),
            "execution": out.get("execution"),
            "dna": out.get("dna"),
        }
    elif analyst == "financial":
        base["desk"] = {
            "capital_allocation": out.get("capital"),
            "guidance": out.get("guidance"),
            "credibility": out.get("credibility"),
        }
    elif analyst == "valuation":
        base["desk"] = {
            "management_quality_premium_inputs": report.get("management_quality"),
            "capital_allocation": out.get("capital"),
            "dna": out.get("dna"),
        }
    elif analyst == "risk":
        base["desk"] = {
            "governance": out.get("governance"),
            "succession": out.get("succession"),
            "open_concerns": out.get("open_concerns"),
        }
    elif analyst in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["open_concerns"] = out.get("open_concerns")
    elif analyst == "research_writer":
        base["writer_blocks"] = {
            "narrative": report.get("executive_summary"),
            "timeline": out.get("timeline"),
            "capital_table": out.get("capital"),
            "dna": out.get("dna"),
        }
    return {"management_intelligence": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "management_intelligence": {
            "enabled": True,
            "version": MII_VERSION,
            "profiles": len(list_profiles()),
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Guidance/credibility/capital/governance must update from filings; no opinion without evidence",
        }
    }


def soft_slice_for_fdi() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "management_intelligence": {
            "enabled": True,
            "version": MII_VERSION,
            "role": "Consume FDI tone/liability changes into credibility & open concerns",
        }
    }


def quality_gates() -> dict[str, Any]:
    out = analyse_management("HDFCBANK")
    report = out.get("report") or {}
    checks = {
        "enabled": is_enabled(),
        "hdfc_found": bool(out.get("found")),
        "guidance_score_present": (out.get("guidance") or {}).get("guidance_score") is not None,
        "credibility_recalculated": (out.get("credibility") or {}).get("n", 0) >= 1,
        "capital_reviewed": (out.get("capital") or {}).get("n", 0) >= 1,
        "governance_scored": (out.get("governance") or {}).get("governance") is not None,
        "dna_classified": bool((out.get("dna") or {}).get("primary")),
        "decision_journal_updated": len(out.get("decision_journal") or []) >= 1,
        "evidence_present": (out.get("evidence") or {}).get("count", 0) >= 1,
        "no_buy_sell": "buy rating" not in (report.get("text") or "").lower(),
        "flags": flags_dict().get("MANAGEMENT_INTELLIGENCE") is True,
    }
    return {"passed": all(checks.values()), "checks": checks, "mii_version": MII_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    out = analyse_management("HDFCBANK")
    report = out.get("report") or {}
    mq = report.get("management_quality") or {}
    dna = out.get("dna") or {}
    concerns = "".join(f"<li>{c}</li>" for c in (out.get("open_concerns") or [])[:8])
    return f"""<!doctype html>
<html><head><title>MII — Management Intelligence</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Management Intelligence Engine</h1>
<p>Primary question: <em>Can this management team be trusted to compound shareholder value?</em></p>
<div class="card">
  <div>Version: {dash.get('mii_version')}</div>
  <div>Profiles: {', '.join(dash.get('profiles') or [])}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFC management score</h2>
  <div>Confidence: <strong>{mq.get('confidence')}</strong></div>
  <div>DNA: <strong>{dna.get('primary')}</strong> · {', '.join(dna.get('secondary') or [])}</div>
  <div>Guidance {mq.get('guidance_score')} · Credibility {mq.get('credibility')} · Execution {mq.get('execution')}</div>
  <div>Capital {mq.get('capital_allocation')} · Governance {mq.get('governance')} · Communication {mq.get('communication')}</div>
  <p>{report.get('cio_brief')}</p>
</div>
<div class="card"><h2>Open concerns</h2><ul>{concerns or '<li>None flagged</li>'}</ul></div>
<p>API: /v1/management-intelligence/* · Flag: MANAGEMENT_INTELLIGENCE</p>
</body></html>"""
