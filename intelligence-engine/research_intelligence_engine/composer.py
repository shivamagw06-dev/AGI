"""Compose full institutional research dossier for one company."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from research_intelligence_engine.confidence import dossier_quality
from research_intelligence_engine.dqiv import validate_dossier, validate_section
from research_intelligence_engine.evidence import load_bundle
from research_intelligence_engine.models import ENGINE_CODE, ENGINE_LABEL, SECTIONS, VERSION
from research_intelligence_engine.sections import SECTION_BUILDERS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_section(symbol: str, section: str, *, bundle: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    key = str(section or "").strip().lower().replace("-", "_")
    if key in {"financial_quality", "financialquality"}:
        key = "financial_quality"
    if key in {"capital_allocation", "capitalallocation"}:
        key = "capital_allocation"
    builder = SECTION_BUILDERS.get(key)
    if not builder:
        return {"ok": False, "error": f"unknown_section:{section}", "engine": ENGINE_CODE}
    pack = bundle or load_bundle(ticker)
    out = builder(pack)
    gate = validate_section(out)
    out["dqiv"] = gate
    out["symbol"] = ticker
    out["section"] = key
    out["engine"] = ENGINE_CODE
    out["version"] = VERSION
    out["generated_at"] = _now()
    if not gate["ok"]:
        out["ok"] = False
        out["status"] = "REJECT"
    return out


def build_dossier(symbol: str) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required", "engine": ENGINE_CODE}
    bundle = load_bundle(ticker)
    sections: dict[str, Any] = {}
    confidences: dict[str, dict[str, Any]] = {}
    for name in SECTIONS:
        if name == "confidence":
            continue
        sec = build_section(ticker, name, bundle=bundle)
        sections[name] = sec
        confidences[name] = sec.get("confidence") or {}

    quality = dossier_quality(confidences, bundle.get("inputs_present") or {})
    sections["confidence"] = {
        "ok": True,
        "title": "Confidence Engine",
        "status": "ok",
        "findings": [
            f"Research confidence: {quality['research_confidence']}.",
            f"Coverage of core inputs: {quality['coverage_pct']}%.",
            f"Section confidence mix — High {quality['distribution']['High']}, "
            f"Medium {quality['distribution']['Medium']}, Low {quality['distribution']['Low']}.",
        ],
        "summary": f"Research confidence {quality['research_confidence']} ({quality['score']}).",
        "explainability": {
            "observed": ["section_confidence_scores", "input_presence"],
            "derived": ["research_quality_score"],
            "inferred": [],
        },
        "evidence": [{"source": "rie.confidence"}],
        "confidence": {
            "confidence": quality["research_confidence"],
            "score": quality["score"],
        },
        "research_quality": quality,
    }

    executive = sections.get("executive") or {}
    dossier = {
        "ok": True,
        "symbol": ticker,
        "company_name": (bundle.get("master") or {}).get("company_name"),
        "sector": (bundle.get("master") or {}).get("sector"),
        "industry": (bundle.get("master") or {}).get("industry"),
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "generated_at": _now(),
        "executive_summary": executive.get("summary"),
        "sections": sections,
        "research_quality": quality,
        "inputs_present": bundle.get("inputs_present"),
        "recommendation": None,
        "investment_rating": None,
        "reads_from": [
            "institutional_warehouse",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "valuation_policy",
            "ownership_intelligence",
        ],
    }
    gate = validate_dossier(dossier)
    dossier["dqiv"] = gate
    if not gate["ok"]:
        dossier["ok"] = False
        dossier["status"] = "REJECT"
    else:
        dossier["status"] = "PASS"
    _persist_summary(dossier)
    return dossier


def _persist_summary(dossier: dict[str, Any]) -> None:
    """Best-effort write of dossier summary for coverage dashboards."""
    try:
        from institutional_warehouse import gateway

        quality = dossier.get("research_quality") or {}
        row = {
            "symbol": dossier.get("symbol"),
            "as_of": (dossier.get("generated_at") or "")[:10],
            "research_confidence": quality.get("research_confidence"),
            "score": quality.get("score"),
            "coverage_pct": quality.get("coverage_pct"),
            "status": dossier.get("status"),
            "executive_summary": (dossier.get("executive_summary") or "")[:500],
            "sections_ok": sum(
                1 for k, v in (dossier.get("sections") or {}).items()
                if k != "confidence" and v.get("ok")
            ),
            "dqiv": (dossier.get("dqiv") or {}).get("status"),
        }
        gateway.write(
            "rie_company_dossier",
            [row],
            source=ENGINE_CODE,
            actor="rie",
            reason="rie_dossier_summary",
        )
    except Exception:
        pass
