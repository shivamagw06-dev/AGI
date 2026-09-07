"""Phase 5 — company evidence requirements before institutional recommendations."""

from __future__ import annotations

from typing import Any


REQUIRED_EVIDENCE_TYPES = (
    "latest_annual_report",
    "latest_quarterly_results",
    "latest_investor_presentation",
    "recent_earnings_call",
    "material_announcements",
    "financial_statements",
    "valuation_metrics",
    "sector_benchmarks",
)


def assess_company_evidence(
    ticker: str | None,
    *,
    kip: Any | None = None,
    eve: Any | None = None,
    aws: Any | None = None,
    ve_pack: dict[str, Any] | None = None,
    iie_pack: dict[str, Any] | None = None,
    supplied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-assess whether institutional company evidence is sufficient for a recommendation."""
    present: dict[str, bool] = {k: False for k in REQUIRED_EVIDENCE_TYPES}
    details: list[dict[str, Any]] = []
    t = (ticker or "").upper() or None

    # Explicit supplied evidence (tests / admin)
    for k, v in (supplied or {}).items():
        if k in present and v:
            present[k] = True
            details.append({"type": k, "source": "supplied"})

    # VE pack implies some valuation metrics / statements may exist
    if isinstance(ve_pack, dict) and ve_pack:
        if ve_pack.get("latest_valuation") or ve_pack.get("assumptions") or ve_pack.get("questions"):
            present["valuation_metrics"] = True
            details.append({"type": "valuation_metrics", "source": "ve"})
        company = ve_pack.get("company") or {}
        if isinstance(company, dict) and (company.get("latest") or company.get("history")):
            present["financial_statements"] = True
            details.append({"type": "financial_statements", "source": "ve.company"})

    # IIE pack
    if isinstance(iie_pack, dict) and iie_pack.get("company"):
        present["sector_benchmarks"] = True
        details.append({"type": "sector_benchmarks", "source": "iie"})

    # EVE verified evidence
    if eve is not None and t:
        try:
            pack = eve.consult(t, limit=8) if hasattr(eve, "consult") else None
            if isinstance(pack, dict):
                hits = pack.get("hits") or []
                if hits:
                    present["material_announcements"] = True
                    details.append({"type": "material_announcements", "source": "eve", "count": len(hits)})
                company = pack.get("company") or {}
                if isinstance(company, dict) and (company.get("evidence") or company.get("statements")):
                    present["financial_statements"] = True
                    details.append({"type": "financial_statements", "source": "eve.company"})
        except Exception:
            pass

    # KIP documents
    if kip is not None and t:
        try:
            docs = []
            if hasattr(kip, "search"):
                res = kip.search(t, limit=12)
                docs = getattr(res, "documents", None) or (res.get("documents") if isinstance(res, dict) else []) or []
            if hasattr(kip, "client_search"):
                # already covered elsewhere; skip heavy path
                pass
            for d in docs[:20]:
                blob = " ".join(
                    str(x)
                    for x in (
                        getattr(d, "title", None) or (d.get("title") if isinstance(d, dict) else ""),
                        getattr(d, "document_type", None) or (d.get("document_type") if isinstance(d, dict) else ""),
                        " ".join(getattr(d, "tags", None) or (d.get("tags") if isinstance(d, dict) else []) or []),
                    )
                ).lower()
                if "annual" in blob or "20-f" in blob or "year ended" in blob:
                    present["latest_annual_report"] = True
                if any(x in blob for x in ("quarter", "q1", "q2", "q3", "q4", "result")):
                    present["latest_quarterly_results"] = True
                if "presentation" in blob or "investor" in blob:
                    present["latest_investor_presentation"] = True
                if "transcript" in blob or "earnings call" in blob or "conference call" in blob:
                    present["recent_earnings_call"] = True
                if "announcement" in blob or "filing" in blob or "exchange" in blob:
                    present["material_announcements"] = True
        except Exception:
            pass

    # AWS company dossier soft
    if aws is not None and t:
        try:
            co = aws.company(t) if hasattr(aws, "company") else None
            if isinstance(co, dict) and co:
                if co.get("financials") or co.get("statements"):
                    present["financial_statements"] = True
                if co.get("valuation"):
                    present["valuation_metrics"] = True
                if co.get("news") or co.get("announcements"):
                    present["material_announcements"] = True
        except Exception:
            pass

    missing = [k for k, ok in present.items() if not ok]
    # Institutional bar: require core pack (results + statements + valuation + at least one narrative source)
    core = [
        "latest_quarterly_results",
        "financial_statements",
        "valuation_metrics",
    ]
    narrative = [
        "latest_annual_report",
        "latest_investor_presentation",
        "recent_earnings_call",
        "material_announcements",
    ]
    core_ok = all(present[k] for k in core)
    narrative_ok = any(present[k] for k in narrative)
    sufficient = bool(t) and core_ok and narrative_ok

    return {
        "ticker": t,
        "sufficient": sufficient,
        "present": present,
        "missing": missing,
        "core_ok": core_ok,
        "narrative_ok": narrative_ok,
        "details": details[:30],
        "recommendation_policy": (
            "institutional_recommendation_allowed"
            if sufficient
            else "insufficient_company_evidence_for_institutional_recommendation"
        ),
        "message": (
            None
            if sufficient
            else "Insufficient company evidence for institutional recommendation."
        ),
    }
