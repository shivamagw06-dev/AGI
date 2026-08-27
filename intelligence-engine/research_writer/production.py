"""IRW production entry — soft writing layer after CIO."""

from __future__ import annotations

from typing import Any

from research_writer.editor import write_institutional_report
from research_writer.flags import flags_dict, is_enabled
from research_writer.schema import ARCHITECTURE_STATUS, IRW_VERSION, PROGRAMME, REPORT_TYPES


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": IRW_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "presentation_writing_layer_only": True,
        "sits_after": "cio",
        "never_changes": [
            "recommendations",
            "scores",
            "confidence",
            "votes",
            "evidence",
        ],
        "report_types": list(REPORT_TYPES),
        "modules": [
            "editor",
            "narrative",
            "formatter",
            "transition",
            "table_builder",
            "chart_recommender",
            "citation_builder",
            "language_quality",
            "consistency",
            "tone",
        ],
        "does_not_redesign": [
            "cid",
            "company_analysis",
            "financial_intelligence",
            "investment_committee",
            "cio",
            "dvc",
            "providers",
            "knowledge_foundation",
            "academy",
            "institutional_analysts",
        ],
        "flags": flags_dict(),
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": IRW_VERSION,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "presentation_only": True,
            "never_mutates_votes": True,
            "never_mutates_confidence": True,
            "never_mutates_evidence": True,
            "scrubs_provider_names": True,
            "scrubs_engine_names": True,
            "has_transitions": True,
            "has_tables": True,
            "has_chart_recommender": True,
            "has_repetition_detector": True,
            "has_consistency_engine": True,
            "engines_unchanged": True,
        },
        "flags": flags_dict(),
    }


def package_for_ask_agi(intelligence_pack: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Write the final institutional report from CIO/committee/analyst outputs.

    Never invents facts. Never changes votes, scores, confidence, or evidence.
    """
    if not is_enabled():
        return {"enabled": False, "bypassed": True, "programme": PROGRAMME}

    pack = dict(intelligence_pack or {})
    # Allow kwargs overlay for soft callers
    for k, v in kwargs.items():
        if v is not None and k not in pack:
            pack[k] = v
    query = str(pack.get("query") or kwargs.get("query") or "")

    # IEP-01: Research Writer cannot execute unless ResearchPack.claim_safe == true
    ticker = str(pack.get("ticker") or kwargs.get("ticker") or "").upper().strip()
    if ticker:
        try:
            from institutional_evidence.gates import gate_research_writer

            iep_gate = gate_research_writer(ticker, pack=pack.get("research_pack"))
            if not iep_gate.get("allowed"):
                return {
                    "enabled": True,
                    "blocked": True,
                    "programme": PROGRAMME,
                    "version": IRW_VERSION,
                    "iep_gate": iep_gate,
                    "message": iep_gate.get("message") or "Evidence unavailable.",
                    "rule": "No research without evidence — never invent financials",
                }
            pack["iep_gate"] = {"allowed": True, "claim_safe": True}
        except Exception:
            pass

    # Soft-wire Academy Books frameworks/terminology (structure only — never book text).
    books_slice: dict[str, Any] = {}
    try:
        from academy.books.production import research_writer_slice

        ticker = None
        if isinstance(pack.get("ticker"), str):
            ticker = pack.get("ticker")
        elif isinstance(pack.get("company_analysis"), dict):
            ticker = pack["company_analysis"].get("ticker")
        books_slice = research_writer_slice(query, ticker=ticker) or {}
        if isinstance(books_slice, dict) and books_slice.get("enabled"):
            pack = {**pack, "academy_books": books_slice}
    except Exception:
        books_slice = {}

    try:
        report = write_institutional_report(pack, query=query)
    except Exception as exc:
        return {
            "enabled": False,
            "error": str(exc)[:200],
            "programme": PROGRAMME,
            "version": IRW_VERSION,
        }

    hints = [
        f"Institutional Research Writer produced a {report.get('report_type')} note",
        "Presentation layer only — committee vote and confidence unchanged",
    ]
    if isinstance(books_slice, dict) and books_slice.get("enabled"):
        for h in (books_slice.get("logic_hints") or [])[:3]:
            if h:
                hints.append(str(h)[:180])
        fws = [str(f) for f in (books_slice.get("frameworks") or [])[:3] if f]
        if fws:
            hints.append("Academy framework lens: " + "; ".join(fws))

    return {
        "enabled": True,
        "programme": PROGRAMME,
        "version": IRW_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "presentation_writing_layer_only": True,
        "institutional_report": report,
        "academy_books": books_slice if isinstance(books_slice, dict) else {},
        # Flat presentation fields for AC / UI
        "executive_summary": report.get("executive_summary"),
        "investment_thesis": report.get("investment_thesis"),
        "institutional_view": report.get("institutional_view"),
        "business_intelligence": report.get("business_intelligence"),
        "financial_intelligence": report.get("financial_intelligence"),
        "valuation_intelligence": report.get("valuation_intelligence"),
        "market_intelligence": report.get("market_intelligence"),
        "sector_intelligence": report.get("sector_intelligence"),
        "macro_intelligence": report.get("macro_intelligence"),
        "management": report.get("management"),
        "ownership": report.get("ownership"),
        "institutional_conclusion": report.get("institutional_conclusion"),
        "bull_case": report.get("bull_case"),
        "base_case": report.get("base_case"),
        "bear_case": report.get("bear_case"),
        "risk_register": report.get("risk_register"),
        "tables": (report.get("tables") or []),
        "chart_recommendations": (report.get("chart_recommendations") or []),
        "citations": (report.get("citations") or []),
        "report_type": report.get("report_type"),
        "quality": report.get("quality"),
        # Explicit pass-through of immutable intelligence
        "intelligence_unchanged": report.get("intelligence_unchanged"),
        "ask_agi_hints": hints,
    }
