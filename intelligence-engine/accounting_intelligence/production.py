"""ACI production facade — soft layer, no redesign."""

from __future__ import annotations

from typing import Any

from accounting_intelligence.flags import flags_dict, is_enabled
from accounting_intelligence.pipeline import analyse_accounting
from accounting_intelligence.profiles.packs import list_profiles
from accounting_intelligence.schema import ACI_VERSION


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_ACCOUNTING_INTELLIGENCE_ENGINE",
        "version": ACI_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Can the financial statements be trusted?",
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "not_an_engine_redesign": True,
    }


def dashboard() -> dict[str, Any]:
    return {
        "programme": "AGIB_ACCOUNTING_INTELLIGENCE_ENGINE",
        "aci_version": ACI_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Can the financial statements be trusted?",
        "flags": flags_dict(),
        "profiles": list_profiles(),
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


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "aci_version": ACI_VERSION}
    out = analyse_accounting(ticker)
    return {"enabled": True, **out}


def analyse(ticker: str) -> dict[str, Any]:
    return company(ticker)


def history(ticker: str) -> dict[str, Any]:
    out = analyse_accounting(ticker)
    return {
        "enabled": is_enabled(),
        "aci_version": ACI_VERSION,
        "ticker": out.get("ticker") or ticker,
        "found": out.get("found"),
        "timeline": out.get("timeline") or [],
        "thesis_events": out.get("thesis_events") or [],
        "behaviour": out.get("behaviour"),
        "confidence_history_note": "Append-only timeline; denser quarterly series via FIL expand coverage",
    }


def soft_slice_for_analyst(ticker: str, *, analyst: str = "financial") -> dict[str, Any]:
    if not is_enabled():
        return {}
    out = analyse_accounting(ticker)
    if not out.get("found"):
        return {"accounting_intelligence": {"enabled": True, "found": False, "ticker": ticker}}
    report = out.get("report") or {}
    base: dict[str, Any] = {
        "enabled": True,
        "version": ACI_VERSION,
        "ticker": out["ticker"],
        "confidence": (out.get("confidence") or {}).get("confidence"),
        "accounting_quality_score": report.get("accounting_quality_score"),
        "behaviour": (out.get("behaviour") or {}).get("primary"),
        "manipulation_risk": (out.get("manipulation") or {}).get("manipulation_risk"),
        "rule": "Ask whether reported numbers can be trusted — not what the numbers were",
    }
    if analyst == "business":
        base["desk"] = {
            "summary": report.get("executive_summary"),
            "behaviour": out.get("behaviour"),
            "quality_score": report.get("accounting_quality_score"),
        }
    elif analyst == "financial":
        base["desk"] = {
            "earnings": out.get("earnings"),
            "cash": out.get("cash"),
            "accruals": out.get("accruals"),
            "revenue": out.get("revenue"),
            "working_capital": out.get("working_capital"),
            "balance_sheet": out.get("balance_sheet"),
            "policies": out.get("policies"),
            "forensic": out.get("forensic"),
            "manipulation": out.get("manipulation"),
        }
    elif analyst == "valuation":
        base["desk"] = {
            "adjusted_earnings_quality": out.get("earnings"),
            "cash_backed_valuation": out.get("cash"),
            "behaviour": out.get("behaviour"),
            "accounting_quality_score": report.get("accounting_quality_score"),
        }
    elif analyst == "risk":
        base["desk"] = {
            "manipulation": out.get("manipulation"),
            "forensic": out.get("forensic"),
            "open_concerns": out.get("open_concerns"),
            "policies": out.get("policies"),
        }
    elif analyst in {"committee", "cio"}:
        base["committee"] = report.get("committee")
        base["cio_brief"] = report.get("cio_brief")
        base["open_concerns"] = out.get("open_concerns")
    elif analyst == "research_writer":
        base["writer_blocks"] = {
            "narrative": report.get("executive_summary"),
            "tables": {
                "earnings_quality": out.get("earnings"),
                "cash_quality": out.get("cash"),
                "forensic": {
                    "beneish_m": ((out.get("forensic") or {}).get("beneish") or {}).get("beneish_m"),
                    "piotroski_f": ((out.get("forensic") or {}).get("piotroski") or {}).get("piotroski_f"),
                    "altman_z": ((out.get("forensic") or {}).get("altman") or {}).get("altman_z"),
                },
            },
            "timeline": out.get("timeline"),
            "behaviour": out.get("behaviour"),
        }
    return {"accounting_intelligence": base}


def soft_slice_for_irs() -> dict[str, Any]:
    if not is_enabled():
        return {}
    return {
        "accounting_intelligence": {
            "enabled": True,
            "version": ACI_VERSION,
            "profiles": len(list_profiles()),
            "quality_gates_passed": quality_gates().get("passed"),
            "rule": "Earnings/cash/WC/policy/Beneish/Piotroski must update from filings; no opinion without evidence",
        }
    }


def soft_slice_for_stack() -> dict[str, Any]:
    return soft_slice_for_irs()


def quality_gates() -> dict[str, Any]:
    out = analyse_accounting("HDFCBANK")
    report = out.get("report") or {}
    forensic = out.get("forensic") or {}
    checks = {
        "enabled": is_enabled(),
        "hdfc_found": bool(out.get("found")),
        "earnings_quality_updated": (out.get("earnings") or {}).get("earnings_quality") is not None,
        "cash_quality_updated": (out.get("cash") or {}).get("cash_quality") is not None,
        "working_capital_analysed": (out.get("working_capital") or {}).get("working_capital") is not None,
        "revenue_recognition_reviewed": (out.get("revenue") or {}).get("revenue_recognition") is not None,
        "policy_changes_detected": (out.get("policies") or {}).get("accounting_consistency") is not None,
        "beneish_calculated": (forensic.get("beneish") or {}).get("beneish_m") is not None,
        "piotroski_calculated": (forensic.get("piotroski") or {}).get("piotroski_f") is not None,
        "behaviour_classified": bool((out.get("behaviour") or {}).get("primary")),
        "evidence_present": (out.get("evidence") or {}).get("count", 0) >= 1,
        "no_opinion_without_evidence": (out.get("evidence") or {}).get("count", 0) >= 1,
        "no_buy_sell": "buy rating" not in (report.get("text") or "").lower(),
        "flags": flags_dict().get("ACCOUNTING_INTELLIGENCE") is True,
    }
    return {"passed": all(checks.values()), "checks": checks, "aci_version": ACI_VERSION}


def admin_page() -> str:
    dash = dashboard()
    gates = quality_gates()
    out = analyse_accounting("HDFCBANK")
    report = out.get("report") or {}
    aq = report.get("accounting_quality") or {}
    behaviour = out.get("behaviour") or {}
    forensic = out.get("forensic") or {}
    concerns = "".join(f"<li>{c}</li>" for c in (out.get("open_concerns") or [])[:8])
    return f"""<!doctype html>
<html><head><title>ACI — Accounting Intelligence</title>
<style>
body{{font-family:Georgia,serif;background:#0f1419;color:#e7ecf1;margin:2rem}}
h1{{letter-spacing:.04em}} .card{{border:1px solid #2a3440;padding:1rem 1.25rem;margin:1rem 0}}
.ok{{color:#7dcea0}} .bad{{color:#f5b7b1}}
</style></head><body>
<h1>Accounting Intelligence Engine</h1>
<p>Primary question: <em>Can the financial statements be trusted?</em></p>
<div class="card">
  <div>Version: {dash.get('aci_version')}</div>
  <div>Profiles: {', '.join(dash.get('profiles') or [])}</div>
  <div class="{'ok' if gates.get('passed') else 'bad'}">Quality gates: {'PASSED' if gates.get('passed') else 'FAILED'}</div>
</div>
<div class="card"><h2>HDFC accounting score</h2>
  <div>Quality: <strong>{aq.get('score')}</strong> · Confidence <strong>{aq.get('confidence')}</strong></div>
  <div>Behaviour: <strong>{behaviour.get('primary')}</strong> · {', '.join(behaviour.get('secondary') or [])}</div>
  <div>Cash {aq.get('cash_quality')} · Earnings {aq.get('earnings_quality')} · WC {aq.get('working_capital')}</div>
  <div>Beneish M {((forensic.get('beneish') or {}).get('beneish_m'))} · Piotroski F {((forensic.get('piotroski') or {}).get('piotroski_f'))}</div>
  <p>{report.get('cio_brief')}</p>
</div>
<div class="card"><h2>Open concerns / manipulation alerts</h2><ul>{concerns or '<li>None flagged</li>'}</ul></div>
<p>API: /v1/accounting-intelligence/* · Flag: ACCOUNTING_INTELLIGENCE</p>
</body></html>"""
