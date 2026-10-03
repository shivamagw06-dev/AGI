"""Build a stable, evidence-first answer object for Ask AGI clients."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


VERSION = "ask-answer-pack-v1.0.0"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any, *, limit: int = 8) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)[:limit]
    if value is not None and not isinstance(value, dict) and _text(value):
        return [value]
    return []


def _text(value: Any) -> str | None:
    value = str(value or "").strip()
    return value or None


def _first(*values: Any) -> str | None:
    for value in values:
        if text := _text(value):
            return text
    return None


def _evidence_refs(rows: Iterable[Any], *, limit: int = 12) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        nested = raw.get("items") if isinstance(raw.get("items"), list) else None
        if nested is not None:
            for ref in _evidence_refs(nested, limit=limit):
                key = (str(ref.get("source") or ""), str(ref.get("title") or ""))
                if key not in seen:
                    seen.add(key)
                    refs.append(ref)
            continue
        title = _first(raw.get("title"), raw.get("claim"), raw.get("summary"))
        source = _first(raw.get("source"), raw.get("provider"), raw.get("type"))
        if not title and not source:
            continue
        ref = {
            "title": title,
            "source": source,
            "as_of": _first(raw.get("as_of"), raw.get("date"), raw.get("published_at")),
            "url": _first(raw.get("url"), raw.get("source_url")),
        }
        key = (str(source or ""), str(title or ""))
        if key not in seen:
            seen.add(key)
            refs.append(ref)
        if len(refs) >= limit:
            break
    return refs[:limit]


def build_answer_pack(
    *,
    question: str,
    ticker: str | None,
    executive: str,
    confidence: float | int | None,
    company_analysis: dict[str, Any] | None = None,
    company_dossier: dict[str, Any] | None = None,
    investment_thesis: Any = None,
    bull_case: list[Any] | None = None,
    bear_case: list[Any] | None = None,
    risks: list[Any] | None = None,
    catalysts: list[Any] | None = None,
    valuation: Any = None,
    evidence_used: list[Any] | None = None,
    supporting_evidence: list[Any] | None = None,
    freshness: Any = None,
    quality_gates: dict[str, Any] | None = None,
    knowledge_gaps: list[Any] | None = None,
) -> dict[str, Any]:
    ca = _dict(company_analysis)
    dossier = _dict(company_dossier)
    identity = _dict(ca.get("identity"))
    financial = _dict(ca.get("financial_intelligence"))
    business_quality = _dict(ca.get("business_quality"))
    valuation_block = _dict(ca.get("valuation_intelligence"))
    readiness = _dict(ca.get("recommendation_readiness"))
    dossier_risks = _dict(dossier.get("risks"))

    financial_summary = _first(
        financial.get("narrative"),
        financial.get("financial_health"),
    )
    valuation_summary = _first(
        valuation_block.get("narrative"),
        _dict(valuation).get("label") if isinstance(valuation, dict) else valuation,
    )
    gaps = [str(x) for x in _list(knowledge_gaps, limit=12) if _text(x)]
    for missing in _list(readiness.get("missing"), limit=12):
        text = _text(missing)
        if text and text not in gaps:
            gaps.append(text)

    risk_rows = [str(x) for x in _list(risks) if _text(x)]
    if not risk_rows:
        for group in dossier_risks.values():
            if isinstance(group, list):
                risk_rows.extend(str(x) for x in group[:3] if _text(x))

    return {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "direct_answer": executive,
        "company": {
            "ticker": ticker,
            "name": _first(identity.get("company_name"), dossier.get("company_name"), ticker),
            "sector": _first(identity.get("sector"), identity.get("sector_id")),
            "industry": identity.get("industry"),
            "geography": identity.get("geography"),
        },
        "business": {
            "overview": _first(
                ca.get("business_overview"),
                identity.get("business_model"),
                dossier.get("business_description"),
                dossier.get("overview"),
            ),
            "quality_score": business_quality.get("business_quality_score"),
            "quality_grade": business_quality.get("grade"),
            "quality_summary": business_quality.get("summary"),
        },
        "financials": {
            "summary": financial_summary,
            "health": financial.get("financial_health"),
            "growth": financial.get("growth"),
            "margins": financial.get("margins"),
            "cash_flow": financial.get("cash_flow"),
            "returns": financial.get("returns"),
            "balance_sheet": financial.get("balance_sheet"),
            "monitor": _list(financial.get("what_deserves_monitoring")),
        },
        "valuation": {
            "summary": valuation_summary,
            "current_pe": valuation_block.get("current_pe"),
            "forward_pe": valuation_block.get("forward_pe"),
            "price_to_book": valuation_block.get("pb"),
            "ev_ebitda": valuation_block.get("ev_ebitda"),
            "versus_history_pct": valuation_block.get("premium_discount_vs_history_pct"),
            "versus_peers_pct": valuation_block.get("premium_discount_vs_peers_pct"),
        },
        "investment_case": {
            "thesis": _text(investment_thesis),
            "bull_case": [str(x) for x in _list(bull_case) if _text(x)],
            "bear_case": [str(x) for x in _list(bear_case) if _text(x)],
            "risks": risk_rows[:8],
            "catalysts": [str(x) for x in _list(catalysts) if _text(x)],
        },
        "evidence": _evidence_refs(
            [*(evidence_used or []), *(supporting_evidence or [])]
        ),
        "freshness": freshness,
        "confidence": confidence,
        "knowledge_gaps": gaps[:12],
        "governance": {
            "quality_gates": _dict(quality_gates),
            "recommendation_gate": readiness.get("gate"),
            "recommendation_readiness_pct": readiness.get("overall"),
            "execution_advice": False,
            "rule": "Research evidence may inform analysis but cannot bypass AGI validation or execution gates.",
        },
    }
