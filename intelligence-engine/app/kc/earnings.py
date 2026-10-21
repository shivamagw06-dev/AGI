"""Earnings memory — quarterly results update living company knowledge (Phase 7)."""

from __future__ import annotations

import re
from typing import Any

from app.aws.adapters import dump
from app.kf.extract import extract_research_object
from app.kf.merge import bump_version, merge_list, merge_string
from app.kf.models import CompanyKnowledgeObject
from app.kf.scoring import confidence_score


_EARNINGS_HINT = re.compile(
    r"\b(earnings|results|quarter|q[1-4]|fy\d{2}|guidance|margin|revenue)\b",
    re.I,
)


def is_earnings_doc(doc: Any) -> bool:
    d = dump(doc) if not isinstance(doc, dict) else doc
    if not isinstance(d, dict):
        return False
    document = d.get("document") if isinstance(d.get("document"), dict) else {}
    dtype = str(document.get("document_type") or d.get("document_type") or "").lower()
    title = str(document.get("title") or d.get("title") or "")
    if "earnings" in dtype or dtype == "earnings_transcript":
        return True
    return bool(_EARNINGS_HINT.search(title))


def apply_earnings_memory(kf: Any, doc: Any) -> dict[str, Any]:
    if not is_earnings_doc(doc):
        return {"accepted": False, "reason": "not_earnings"}

    d = dump(doc) if not isinstance(doc, dict) else doc
    document = d.get("document") if isinstance(d.get("document"), dict) else {}
    research = d.get("research") if isinstance(d.get("research"), dict) else {}
    investment = d.get("investment") if isinstance(d.get("investment"), dict) else {}
    knowledge = d.get("knowledge") if isinstance(d.get("knowledge"), dict) else {}

    title = str(document.get("title") or d.get("title") or "")
    summary = str(knowledge.get("summary") or research.get("investment_thesis") or "")[:800]
    companies = [str(x).upper() for x in (investment.get("tickers") or [])][:12]
    risks = [str(x) for x in (research.get("risks") or [])][:12]
    catalysts = [str(x) for x in (research.get("catalysts") or [])][:12]
    doc_id = str(d.get("document_id") or document.get("document_id") or "")

    # Standard extract path compounds KF research memory once.
    if doc_id and doc_id not in kf.store.extracts:
        if extract_research_object(doc) is not None:
            kf.pipeline.ingest_document(doc)

    updated: list[str] = []
    for t in companies:
        kf.pipeline.ensure_seeded()
        if t not in kf.store.companies:
            kf.pipeline._seed_company({"ticker": t, "name": t, "sector": "", "industry": ""})
        co = kf.store.companies[t]
        data = co.model_dump(mode="json")
        data["financial_history"] = merge_list(
            data.get("financial_history"),
            [f"Earnings update: {title}", summary[:240] if summary else None],
        )
        if "margin" in (summary + title).lower():
            data["margins"] = merge_list(data.get("margins"), [summary[:200] or title])
        if "guidance" in (summary + title).lower():
            data["key_catalysts"] = merge_list(data.get("key_catalysts"), [f"Guidance update from {title}"])
        data["key_risks"] = merge_list(data.get("key_risks"), risks)
        data["key_catalysts"] = merge_list(data.get("key_catalysts"), catalysts)
        data["related_research"] = merge_list(data.get("related_research"), [doc_id, f"earnings:{title}"])
        # House-view / prediction impact markers
        if summary:
            data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", summary)
        data["historical_house_views"] = merge_list(
            data.get("historical_house_views"),
            [{"source": "earnings", "title": title, "summary": summary[:280], "document_id": doc_id}],
            limit=24,
        )
        meta = bump_version(dict(data["meta"]), reason=f"earnings memory {doc_id or title}")
        meta["sources"] = merge_list(meta.get("sources"), ["earnings", "agi_research"])
        meta["document_ids"] = merge_list(meta.get("document_ids"), [doc_id])
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("latest_thesis")),
            n_sources=len(meta.get("document_ids") or []),
            source_reliability=0.9,
            n_structured_fields=sum(bool(x) for x in (data.get("financial_history"), data.get("margins"), data.get("key_risks"))),
            has_house_view=True,
            has_predictions=bool(data.get("predictions")),
        )
        meta["freshness"] = 1.0
        data["meta"] = meta
        kf.store.upsert_company(CompanyKnowledgeObject.model_validate(data))
        updated.append(t)

    return {"accepted": True, "companies_updated": updated, "document_id": doc_id, "title": title}


def earnings_company_keys(kf: Any) -> set[str]:
    keys: set[str] = set()
    for co in kf.store.companies.values():
        blob = " ".join(str(x) for x in (co.related_research or []) + (co.financial_history or [])).lower()
        if "earnings" in blob or "quarter" in blob or "results" in blob:
            keys.add(co.ticker.upper())
    for ex in kf.store.extracts.values():
        title = (ex.title or "").lower()
        if "earnings" in title or "result" in title or "quarter" in title:
            keys.update(str(c).upper() for c in ex.companies)
    return keys
