"""Read adapters for existing AGI causal relationship formats."""

from __future__ import annotations

import hashlib
from typing import Any

from causal_research_engine.schema import CausalRelationship, EvidenceReference


def _id(prefix: str, source: Any, target: Any, relation: Any) -> str:
    raw = f"{source}|{target}|{relation}"
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:16].upper()}"


def from_cig_edge(edge: dict[str, Any], *, industry: str | None = None, company_id: str | None = None) -> CausalRelationship:
    evidence = tuple(
        EvidenceReference(
            evidence_id=f"CIG-EVIDENCE-{i}-{_id('', edge.get('source'), edge.get('target'), item.get('source'))[-8:]}",
            source_type=str(item.get("kind") or "sector_model"), source_id=str(item.get("source") or "causal_graph"),
            passage=item.get("note"), quality="VALIDATED" if edge.get("validated") else "UNVALIDATED",
        )
        for i, item in enumerate(edge.get("evidence") or [], 1)
    )
    sign = edge.get("direction_sign")
    return CausalRelationship(
        relationship_id=_id("CRE-CIG", edge.get("source"), edge.get("target"), edge.get("relation")),
        cause=str(edge.get("source") or ""), effect=str(edge.get("target") or ""),
        direction="NEGATIVE" if sign == -1 else "POSITIVE" if sign == 1 else "UNKNOWN",
        relationship_type="STRUCTURAL", epistemic_label="OBSERVATION",
        industry=industry, company_id=company_id, strength=_strength(edge.get("strength")),
        confidence=float(edge.get("confidence") or 0), time_lag="UNKNOWN",
        mechanism=str((evidence[0].passage if evidence else "") or "Existing validated CIG transmission edge"),
        evidence=evidence, source_count=len({item.source_id for item in evidence}),
        source_quality="VALIDATED" if edge.get("validated") else "UNVALIDATED",
        status="VALIDATED" if edge.get("validated") and evidence else "PROPOSED",
        created_by="causal_graph_adapter",
    )


def from_ieri_relationship(row: dict[str, Any]) -> CausalRelationship:
    evidence = tuple(
        EvidenceReference(
            evidence_id=f"{row.get('relationship_id')}:evidence:{i}", source_type="economic_relationship",
            source_id=str(row.get("source") or ""), available_at=row.get("available_from"),
            publication_date=row.get("effective_date"), passage=str(text),
            quality="VALIDATED" if (row.get("validation") or {}).get("status") == "validated" else "UNVALIDATED",
        ) for i, text in enumerate(row.get("evidence") or [], 1)
    )
    validation_status = str((row.get("validation") or {}).get("status") or "pending").lower()
    return CausalRelationship(
        relationship_id=str(row.get("relationship_id") or _id("CRE-IERI", row.get("source_entity"), row.get("target_entity"), row.get("relationship_type"))),
        cause=str(row.get("source_entity") or ""), effect=str(row.get("target_entity") or ""),
        direction=_ieri_direction(row), relationship_type=_ieri_type(row),
        epistemic_label="OBSERVATION" if evidence else "HYPOTHESIS",
        strength=_strength(row.get("strength")), confidence=float(row.get("confidence") or 0),
        time_lag=_lag(row.get("time_horizon")), mechanism=str(row.get("semantics") or row.get("notes") or ""),
        evidence=evidence, source_count=len({item.source_id for item in evidence}),
        source_quality="VALIDATED" if validation_status == "validated" else "UNVALIDATED",
        valid_from=row.get("available_from"), observed_period=row.get("effective_date"),
        status="VALIDATED" if validation_status == "validated" and evidence else "PROPOSED",
        version=str(row.get("version") or "cre-v1.0.0"), created_by="ieri_adapter",
    )


def _strength(value: Any) -> str:
    if isinstance(value, (int, float)):
        return "VERY_HIGH" if value >= .85 else "HIGH" if value >= .7 else "MEDIUM" if value >= .45 else "LOW"
    text = str(value or "").upper()
    return {"MODERATE": "MEDIUM", "STRONG": "HIGH", "WEAK": "LOW"}.get(text, text if text in {"VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"} else "UNKNOWN")


def _lag(value: Any) -> str:
    text = str(value or "").upper().replace("-", "_").replace(" ", "_")
    return text if text in {"IMMEDIATE", "DAYS", "WEEKS", "MONTHS", "1_QUARTER", "2_QUARTERS", "3_QUARTERS", "4_QUARTERS", "MULTI_YEAR"} else "UNKNOWN"


def _ieri_direction(row: dict[str, Any]) -> str:
    shock = str(row.get("shock_direction") or row.get("semantics") or "").lower()
    if any(token in shock for token in ("decrease", "negative", "reduce", "compress")): return "NEGATIVE"
    if any(token in shock for token in ("increase", "positive", "raise", "expand")): return "POSITIVE"
    return "UNKNOWN"


def _ieri_type(row: dict[str, Any]) -> str:
    raw = str(row.get("relationship_type") or "").lower()
    if "regulat" in raw: return "REGULATORY"
    if "macro" in raw or "rate" in raw or "currency" in raw: return "MACRO_TRANSMISSION"
    if "financial" in raw: return "FINANCIAL_TRANSMISSION"
    return "STRUCTURAL" if row.get("evidence") else "CAUSAL_HYPOTHESIS"
