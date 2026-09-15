"""Broker knowledge extraction — structured fields, not PDF archives (Phase 6)."""

from __future__ import annotations

import re
from typing import Any

from app.aws.adapters import dump
from app.kf.extract import extract_research_object
from app.kf.merge import bump_version, merge_list, merge_string
from app.kf.models import CompanyKnowledgeObject
from app.kf.scoring import confidence_score, source_reliability


_TARGET_RE = re.compile(
    r"(?:target\s*price|tp|price\s*target)\s*[:=]?\s*(?:rs\.?|₹|inr)?\s*([0-9]{2,6}(?:\.[0-9]+)?)",
    re.I,
)
_RATING_RE = re.compile(
    r"\b(buy|sell|hold|overweight|underweight|neutral|accumulate|reduce|outperform|underperform)\b",
    re.I,
)


def is_broker_doc(doc: Any) -> bool:
    d = dump(doc) if not isinstance(doc, dict) else doc
    if not isinstance(d, dict):
        return False
    document = d.get("document") if isinstance(d.get("document"), dict) else {}
    dtype = str(document.get("document_type") or d.get("document_type") or "").lower()
    source = str(document.get("source") or d.get("source") or "").lower()
    return "broker" in dtype or source == "broker" or dtype in {"sell_side", "buy_side"}


def extract_broker_fields(doc: Any) -> dict[str, Any]:
    d = dump(doc) if not isinstance(doc, dict) else doc
    if not isinstance(d, dict):
        return {}
    document = d.get("document") if isinstance(d.get("document"), dict) else {}
    research = d.get("research") if isinstance(d.get("research"), dict) else {}
    investment = d.get("investment") if isinstance(d.get("investment"), dict) else {}
    content = str(document.get("content") or d.get("content") or "")
    title = str(document.get("title") or d.get("title") or "")
    blob = f"{title}\n{content}\n{research}"

    target = ""
    if research.get("target_prices"):
        target = str((research.get("target_prices") or [""])[0])
    if not target:
        m = _TARGET_RE.search(blob)
        if m:
            target = m.group(1)

    rating = str(research.get("rating") or research.get("recommendation") or "")
    if not rating:
        m = _RATING_RE.search(blob)
        if m:
            rating = m.group(1).title()

    return {
        "document_id": str(d.get("document_id") or document.get("document_id") or ""),
        "title": title,
        "broker": str(document.get("broker") or d.get("broker") or "broker"),
        "target_price": target,
        "rating": rating,
        "investment_thesis": str(research.get("investment_thesis") or "")[:1200],
        "changed_view": str(research.get("changed_view") or research.get("view_change") or "")[:500],
        "risks": [str(x) for x in (research.get("risks") or [])][:12],
        "catalysts": [str(x) for x in (research.get("catalysts") or [])][:12],
        "forecast_changes": [str(x) for x in (research.get("forecast_changes") or research.get("estimate_changes") or [])][:12],
        "consensus": str(research.get("consensus") or "")[:300],
        "companies": [str(x).upper() for x in (investment.get("tickers") or [])][:12],
    }


def apply_broker_knowledge(kf: Any, doc: Any) -> dict[str, Any]:
    """Merge structured broker knowledge into KF company objects."""
    if not is_broker_doc(doc):
        return {"accepted": False, "reason": "not_broker"}

    fields = extract_broker_fields(doc)
    # Compound into KF extract memory once (no duplicate archive).
    doc_id = str(fields.get("document_id") or "")
    if doc_id and doc_id not in kf.store.extracts:
        if extract_research_object(doc) is not None:
            kf.pipeline.ingest_document(doc)

    updated: list[str] = []
    for t in fields.get("companies") or []:
        kf.pipeline.ensure_seeded()
        if t not in kf.store.companies:
            kf.pipeline._seed_company({"ticker": t, "name": t, "sector": "", "industry": ""})
        co = kf.store.companies[t]
        data = co.model_dump(mode="json")
        note_bits = []
        if fields.get("rating"):
            note_bits.append(f"Broker rating: {fields['rating']}")
        if fields.get("target_price"):
            note_bits.append(f"Target price: {fields['target_price']}")
        if fields.get("changed_view"):
            note_bits.append(f"Changed view: {fields['changed_view']}")
        if fields.get("consensus"):
            note_bits.append(f"Consensus: {fields['consensus']}")
        valuation_note = "; ".join(note_bits)
        data["valuation"] = merge_string(data.get("valuation") or "", valuation_note)
        data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", fields.get("investment_thesis") or "")
        data["key_risks"] = merge_list(data.get("key_risks"), fields.get("risks"))
        data["key_catalysts"] = merge_list(data.get("key_catalysts"), fields.get("catalysts"))
        data["financial_history"] = merge_list(
            data.get("financial_history"),
            [f"Broker forecast change: {x}" for x in (fields.get("forecast_changes") or [])],
        )
        data["related_research"] = merge_list(
            data.get("related_research"),
            [fields.get("document_id"), f"broker:{fields.get('broker')}:{fields.get('title')}"],
        )
        meta = bump_version(dict(data["meta"]), reason=f"broker knowledge {fields.get('document_id')}")
        meta["sources"] = merge_list(meta.get("sources"), ["broker", fields.get("broker")])
        meta["document_ids"] = merge_list(meta.get("document_ids"), [fields.get("document_id")])
        meta["source_reliability"] = source_reliability("broker")
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("latest_thesis")),
            n_sources=len(meta.get("document_ids") or []),
            source_reliability=0.8,
            n_structured_fields=sum(bool(x) for x in (fields.get("rating"), fields.get("target_price"), data.get("key_risks"))),
            has_house_view=bool(data.get("latest_thesis")),
        )
        meta["freshness"] = 1.0
        data["meta"] = meta
        kf.store.upsert_company(CompanyKnowledgeObject.model_validate(data))
        updated.append(t)

    return {
        "accepted": True,
        "broker": fields.get("broker"),
        "target_price": fields.get("target_price"),
        "rating": fields.get("rating"),
        "companies_updated": updated,
    }
