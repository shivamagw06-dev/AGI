"""Corporate Event Object — immutable institutional event record."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.corporate_events.provenance import provenance
from knowledge_factory.corporate_events.schema import (
    ICEI_SCHEMA_VERSION,
    ICEI_VERSION,
    IMPACT_DIMENSIONS,
    canonicalize_type,
    category_for,
)


def event_fingerprint(
    *,
    company: str,
    event_type: str,
    announcement_date: str,
    title: str,
    source: str,
) -> str:
    raw = "|".join(
        [
            str(company or "").upper(),
            canonicalize_type(event_type),
            str(announcement_date or "")[:10],
            str(title or "").strip().lower(),
            str(source or "").strip().lower(),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _normalize_impact(impact: dict[str, Any] | None) -> dict[str, str]:
    impact = impact or {}
    out: dict[str, str] = {}
    for dim in IMPACT_DIMENSIONS:
        val = str(impact.get(dim) or "unknown")
        out[dim] = val
    return out


def build_event(
    *,
    company: str,
    event_type: str,
    announcement_date: str,
    title: str,
    source: str,
    collector: str,
    importance: str = "Medium",
    confidence: float = 0.8,
    effective_date: str | None = None,
    available_from: str | None = None,
    evidence: list[str] | str | None = None,
    impact: dict[str, Any] | None = None,
    affected_companies: list[str] | None = None,
    affected_sectors: list[str] | None = None,
    affected_macro: list[str] | None = None,
    sector: str | None = None,
    derived_from: list[str] | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    t = str(company or "").upper()
    et = canonicalize_type(event_type)
    ann = str(announcement_date or "")[:10]
    eff = str(effective_date or ann)[:10]
    avail = str(available_from or ann)[:10]
    if isinstance(evidence, str):
        evidence = [evidence]
    evidence = list(evidence or [])
    aff_cos = list(dict.fromkeys([*(affected_companies or []), t]))
    aff_sec = list(affected_sectors or ([] if not sector else [sector]))
    eid = f"ICEI-{t}-{et}-{ann}-{event_fingerprint(company=t, event_type=et, announcement_date=ann, title=title, source=source)}"

    return {
        "kind": "corporate_event",
        "icei_version": ICEI_VERSION,
        "icei_schema_version": ICEI_SCHEMA_VERSION,
        "event_id": eid,
        "type": et,
        "category": category_for(et),
        "date": str(date or ann)[:10],
        "announcement_date": ann,
        "effective_date": eff,
        "available_from": avail,
        "source": source,
        "company": t,
        "title": title,
        "importance": importance,
        "confidence": round(float(confidence), 4),
        "evidence": evidence,
        "affected_companies": aff_cos,
        "affected_sectors": aff_sec,
        "affected_macro": list(affected_macro or []),
        "impact": _normalize_impact(impact),
        "relationships": {
            "company": t,
            "industry": aff_sec[0] if aff_sec else None,
            "sector": aff_sec[0] if aff_sec else sector,
            "macro": list(affected_macro or []),
            "government": "pending_government_intelligence",
            "commodity": None,
            "portfolio": "institutional_reasoning.ipi",
            "decision": "decision_quality",
            "outcome": None,
            "company_intelligence": f"knowledge_factory.company_intelligence:{t}",
            "historical_depth": f"knowledge_factory.historical_depth.company:{t}",
        },
        "provenance": provenance(
            source=source,
            collector=collector,
            confidence=confidence,
            derived_from=derived_from or ["corporate_event_seed"],
        ),
        "immutable": True,
        "fabricated": False,
        "speculative_forecast": False,
        "note": "Impact fields are structured evidence-backed descriptors, not forecasts.",
    }
