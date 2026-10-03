"""Step 9 — Evidence packing: every major claim traces to institutional sources."""

from __future__ import annotations

from typing import Any


def pack_evidence(
    *,
    identity: dict[str, Any],
    academy_applied: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    sector: dict[str, Any] | None = None,
    business_quality: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    def add(claim: str, source: str, ref: Any = None, confidence: float = 0.7) -> None:
        if not claim:
            return
        items.append(
            {
                "claim": claim,
                "source": source,
                "ref": ref,
                "confidence": confidence,
            }
        )

    if identity.get("business_model"):
        add(identity["business_model"], "cid/identity", identity.get("ticker"), 0.8)
    for c in list((academy_applied or {}).get("applied_concepts") or [])[:6]:
        add(c.get("application") or c.get("title"), "academy", c.get("concept_id") or c.get("title"), 0.75)
    if (financial or {}).get("narrative"):
        add(financial["narrative"], "financial_intelligence", financial.get("sources"), 0.7)
    if (valuation or {}).get("narrative"):
        add(valuation["narrative"], "valuation_intelligence", valuation.get("sources"), 0.7)
    for line in list((sector or {}).get("reasoning") or [])[:3]:
        add(line, "sector_intelligence", sector.get("sector_id"), 0.7)
    if (business_quality or {}).get("summary"):
        add(business_quality["summary"], "business_quality", business_quality.get("business_quality_score"), 0.65)

    if (dvc_pkg or {}).get("quality"):
        add(f"DVC quality: {dvc_pkg.get('quality')}", "dvc", dvc_pkg.get("grades"), 0.8)
    n_leo = len((leo_pkg or {}).get("evidence_objects") or [])
    if n_leo:
        add(f"LEO evidence objects available: {n_leo}", "leo", n_leo, 0.75)
    if cid and cid.get("coverage_score") is not None:
        add(f"CID coverage score: {cid.get('coverage_score')}", "cid", cid.get("coverage_grade"), 0.8)

    return {
        "items": items[:40],
        "count": len(items),
        "policy": "every_statement_references_institutional_source",
        "unsupported_opinions": False,
    }
