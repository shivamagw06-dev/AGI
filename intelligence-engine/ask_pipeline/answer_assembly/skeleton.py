"""Stage 4 — Deterministic answer skeleton (no free-form LLM)."""

from __future__ import annotations

from typing import Any

from ask_pipeline.answer_assembly.schema import SKELETON_SECTIONS


def build_skeleton(
    *,
    question: str,
    intent_v2: str,
    ordered: dict[str, Any],
    gaps: dict[str, Any],
    concept_mode: bool = False,
    as_of: str | None = None,
) -> dict[str, Any]:
    items = ordered.get("ordered") or []
    top = items[:8]
    framework_inputs = ordered.get("framework_inputs") or {}

    sections: dict[str, dict[str, Any]] = {}
    for name in SKELETON_SECTIONS:
        sections[name] = {
            "section": name,
            "bullets": [],
            "evidence_ids": [],
            "status": "planned",
        }

    # Executive summary plan
    sections["executive_summary"]["bullets"] = [
        f"Intent: {intent_v2}",
        "Concept mode" if concept_mode else "Entity-bound analysis",
        f"Point-in-time as_of={as_of}" if as_of else "Current evidence window",
        f"Evidence coverage={gaps.get('coverage')}",
    ]
    sections["executive_summary"]["evidence_ids"] = [i.get("evidence_id") for i in top[:3] if i.get("evidence_id")]

    # Evidence section — ordered institutional facts (titles only, no invention)
    for item in top:
        eid = item.get("evidence_id")
        title = item.get("title") or item.get("evidence_type") or eid
        domain = item.get("domain")
        sections["evidence"]["bullets"].append(f"[{domain}] {title}")
        if eid:
            sections["evidence"]["evidence_ids"].append(eid)

    # Analysis — bind concrete evidence titles (never planning prompts as user text).
    # Concept-mode / education questions must not surface an entity's evidence titles
    # as the analysis lead (the question isn't about that company).
    if not concept_mode:
        for item in top[:6]:
            eid = item.get("evidence_id")
            title = item.get("title") or item.get("evidence_type")
            domain = item.get("domain") or "Evidence"
            if not title:
                continue
            sections["analysis"]["bullets"].append(f"{domain}: {title}")
            if eid:
                sections["analysis"]["evidence_ids"].append(eid)
    # Domain coverage as internal status only (not executive-facing planning prose)
    for domain in (ordered.get("priority_domains") or [])[:5]:
        ids = framework_inputs.get(domain) or []
        if ids:
            sections["analysis"]["evidence_ids"].extend(ids[:2])

    # Framework — bind valuation/accounting/business-model inputs
    for domain in ("ValuationFramework", "Accounting", "BusinessModel", "Industry", "Macro"):
        ids = framework_inputs.get(domain) or []
        if ids:
            sections["framework"]["bullets"].append(f"Framework input domain: {domain}")
            sections["framework"]["evidence_ids"].extend(ids[:4])
    if not sections["framework"]["bullets"]:
        sections["framework"]["bullets"].append("No dedicated framework inputs — use ordered evidence")
        sections["framework"]["status"] = "thin"

    # Risks — from Risk domain + gaps
    for item in items:
        if item.get("domain") == "Risk":
            sections["risks"]["bullets"].append(str(item.get("title") or item.get("evidence_id")))
            if item.get("evidence_id"):
                sections["risks"]["evidence_ids"].append(item["evidence_id"])
    for miss in gaps.get("missing_domains") or []:
        sections["risks"]["bullets"].append(f"Evidence gap: {miss}")
    if not sections["risks"]["bullets"]:
        sections["risks"]["bullets"].append("No explicit risk-domain evidence retrieved")

    # Conclusion plan
    sections["conclusion"]["bullets"] = [
        "Fill from existing reasoning / education path — no unsupported certainty",
        gaps.get("tell_reasoning") or "Coverage assessed",
    ]
    sections["conclusion"]["evidence_ids"] = list(sections["evidence"]["evidence_ids"][:5])

    # Confidence placeholder (filled in Stage 5)
    sections["confidence"]["bullets"] = ["Pending calibration"]

    # Sources
    for item in top:
        cit = item.get("citation") or {}
        src = cit.get("source") or item.get("source")
        doc = cit.get("document_id") or item.get("document_id")
        sections["sources"]["bullets"].append(
            f"{item.get('evidence_id')}: source={src}; doc={doc}; type={item.get('evidence_type')}"
        )
        if item.get("evidence_id"):
            sections["sources"]["evidence_ids"].append(item["evidence_id"])

    return {
        "stage": "answer_skeleton",
        "question": question,
        "intent_v2": intent_v2,
        "sections": sections,
        "section_order": list(SKELETON_SECTIONS),
        "concept_mode": concept_mode,
        "as_of": as_of,
        "fabricated": False,
        "free_form": False,
    }
