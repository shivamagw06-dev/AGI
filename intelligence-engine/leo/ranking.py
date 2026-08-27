"""Evidence ranking — filings first, discard stale, surface conflicts."""

from __future__ import annotations

from typing import Any

from leo.schema import RANK_WEIGHTS


def rank_evidence(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for obj in objects or []:
        o = dict(obj)
        etype = o.get("evidence_type") or "news"
        weight = float(RANK_WEIGHTS.get(etype, 2.5))
        conf = float(o.get("confidence") or 0.5)
        verified_bonus = 0.15 if o.get("verification_status") in {"verified", "provisionally_verified"} else 0.0
        score = (3.0 - weight) + conf + verified_bonus
        o["ranking_score"] = round(score, 4)
        scored.append(o)
    scored.sort(key=lambda x: (-float(x.get("ranking_score") or 0), x.get("evidence_type") or ""))
    return scored


def summarize_usage(objects: list[dict[str, Any]], api_calls: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    docs: list[str] = []
    announcements: list[str] = []
    market: list[str] = []
    macro: list[str] = []
    for o in objects or []:
        et = o.get("evidence_type") or "other"
        by_type[et] = by_type.get(et, 0) + 1
        sid = o.get("source_id") or "unknown"
        by_source[sid] = by_source.get(sid, 0) + 1
        title = o.get("title") or o.get("fact_key") or et
        if et in {"annual_report", "quarterly_results", "investor_presentation", "earnings_transcript", "financial_statements"}:
            docs.append(str(title)[:120])
        elif et == "corporate_announcement":
            announcements.append(str(title)[:120])
        elif et == "market_data":
            market.append(str(title)[:120])
        elif et == "macro":
            macro.append(str(title)[:120])

    sources_queried = [c.get("source_id") for c in api_calls or []]
    sources_used = sorted({o.get("source_id") for o in objects or [] if o.get("source_id")})
    external_sources = [s for s in sources_used if s not in {"internal_research", "eve", "kip", "mee", "sif_kpis"}]
    return {
        "by_type": by_type,
        "by_source": by_source,
        "documents_used": docs[:12],
        "announcements_used": announcements[:12],
        "market_data_used": market[:12],
        "macro_data_used": macro[:12],
        "sources_queried": sources_queried,
        "sources_used": sources_used,
        "external_sources_used": external_sources,
        "external_api_contributed": bool(external_sources),
        "api_calls": api_calls or [],
    }
