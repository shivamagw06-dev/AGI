"""Government Intelligence Object — immutable policy record."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.government_intelligence.provenance import provenance
from knowledge_factory.government_intelligence.schema import IGRI_SCHEMA_VERSION, IGRI_VERSION


def policy_fingerprint(*, policy_id: str, name: str, announcement_date: str, government_body: str) -> str:
    raw = "|".join(
        [
            str(policy_id or "").upper(),
            str(name or "").strip().lower(),
            str(announcement_date or "")[:10],
            str(government_body or "").upper(),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def build_policy(seed: dict[str, Any], *, collector: str = "igri.collectors.seed") -> dict[str, Any]:
    pid = str(seed["policy_id"]).upper()
    ann = str(seed["announcement_date"])[:10]
    eff = str(seed.get("effective_date") or ann)[:10]
    avail = str(seed.get("available_from") or ann)[:10]
    body = str(seed["government_body"]).upper()
    evidence = seed.get("evidence") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    transmission = dict(seed.get("transmission") or {})
    # Ensure transmission schema keys exist (knowledge only)
    transmission.setdefault("primary", [])
    transmission.setdefault("secondary", [])
    transmission.setdefault("beneficiary_industries", [])
    transmission.setdefault("adversely_impacted_industries", [])
    transmission.setdefault("time_horizon", "unknown")
    transmission.setdefault("confidence", float(seed.get("confidence") or 0.7))
    transmission["speculative_forecast"] = False

    relationships = {
        "sector": list(seed.get("affected_sectors") or []),
        "industry": list(seed.get("affected_industries") or []),
        "company": list(seed.get("affected_companies") or []),
        "commodity": list(seed.get("affected_commodities") or []),
        "macro": "knowledge_factory.macro_intelligence",
        "corporate_events": "knowledge_factory.corporate_events",
        "portfolio": "institutional_reasoning.ipi",
        "decision_quality": "decision_quality",
        "outcome": None,
        "company_intelligence": "knowledge_factory.company_intelligence",
        "duplicated_data": False,
    }

    return {
        "kind": "government_intelligence_object",
        "igri_version": IGRI_VERSION,
        "igri_schema_version": IGRI_SCHEMA_VERSION,
        "policy_id": pid,
        "name": seed["name"],
        "policy_type": seed.get("policy_type"),
        "domain": seed.get("domain"),
        "government_body": body,
        "announcement_date": ann,
        "effective_date": eff,
        "available_from": avail,
        "expiry": seed.get("expiry"),
        "jurisdiction": seed.get("jurisdiction") or "India",
        "affected_sectors": list(seed.get("affected_sectors") or []),
        "affected_industries": list(seed.get("affected_industries") or []),
        "affected_companies": list(seed.get("affected_companies") or []),
        "affected_commodities": list(seed.get("affected_commodities") or []),
        "historical_versions": list(seed.get("historical_versions") or []),
        "evidence": list(evidence),
        "source": seed.get("source"),
        "confidence": round(float(seed.get("confidence") or 0.85), 4),
        "impact_level": seed.get("impact_level") or "Medium",
        "instruments": dict(seed.get("instruments") or {}),
        "transmission": transmission,
        "relationships": relationships,
        "notes": seed.get("notes"),
        "provenance": provenance(
            source=str(seed.get("source") or "official"),
            collector=collector,
            confidence=float(seed.get("confidence") or 0.85),
            derived_from=["institutional_policy_seed", pid],
        ),
        "fingerprint": policy_fingerprint(
            policy_id=pid, name=seed["name"], announcement_date=ann, government_body=body
        ),
        "immutable": True,
        "fabricated": False,
        "political_opinion": False,
        "policy_forecast": False,
    }
