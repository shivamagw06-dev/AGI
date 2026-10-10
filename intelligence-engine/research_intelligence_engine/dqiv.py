"""DQIV gates for RIE — reject unsupported / recommendation-shaped output."""

from __future__ import annotations

from typing import Any

from research_intelligence_engine.models import FORBIDDEN_TOKENS


def validate_section(section: dict[str, Any]) -> dict[str, Any]:
    if not section:
        return {"ok": False, "status": "REJECT", "errors": ["empty_section"]}
    errors: list[str] = []
    text = " ".join(str(x) for x in (section.get("findings") or [])) + " " + str(section.get("summary") or "")
    low = f" {text.lower()} "
    for tok in FORBIDDEN_TOKENS:
        if f" {tok} " in low or low.strip() == tok:
            errors.append(f"forbidden_language:{tok}")
    if section.get("ok") is False and section.get("status") == "dqiv_reject":
        errors.append(section.get("error") or "dqiv_reject")
    expl = section.get("explainability") or {}
    if section.get("findings") and not (expl.get("observed") or expl.get("derived") or section.get("evidence")):
        errors.append("missing_explainability")
    if not section.get("confidence"):
        errors.append("missing_confidence")
    if errors:
        return {"ok": False, "status": "REJECT", "errors": errors}
    return {"ok": True, "status": "PASS", "errors": []}


def validate_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    sections = dossier.get("sections") or {}
    if not sections:
        errors.append("no_sections")
    for name, sec in sections.items():
        if name == "confidence":
            continue
        gate = validate_section(sec)
        if not gate["ok"]:
            errors.append(f"{name}:{','.join(gate['errors'])}")
    quality = dossier.get("research_quality") or {}
    if quality.get("recommendation") or quality.get("investment_rating"):
        errors.append("investment_rating_forbidden")
    if errors:
        return {"ok": False, "status": "REJECT", "errors": errors[:40]}
    return {"ok": True, "status": "PASS", "errors": []}
