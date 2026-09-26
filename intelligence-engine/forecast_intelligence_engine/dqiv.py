"""DQIV gates for FIE — reject unsupported / recommendation-shaped output."""

from __future__ import annotations

from typing import Any

from forecast_intelligence_engine.models import FORBIDDEN_TOKENS


def _text_blob(section: dict[str, Any]) -> str:
    parts = list(section.get("findings") or [])
    parts.append(str(section.get("summary") or ""))
    for key in ("assumptions", "outlook", "scenarios"):
        val = section.get(key)
        if isinstance(val, (list, dict)):
            parts.append(str(val))
    return " ".join(str(p) for p in parts)


def validate_section(section: dict[str, Any]) -> dict[str, Any]:
    if not section:
        return {"ok": False, "status": "REJECT", "errors": ["empty_section"]}
    errors: list[str] = []
    low = f" {_text_blob(section).lower()} "
    for tok in FORBIDDEN_TOKENS:
        if f" {tok} " in low or low.strip() == tok:
            errors.append(f"forbidden_language:{tok}")
    if section.get("ok") is False and section.get("status") == "dqiv_reject":
        errors.append(section.get("error") or "dqiv_reject")
    expl = section.get("explainability") or {}
    if section.get("findings") and not (
        expl.get("observed") or expl.get("derived") or expl.get("assumed") or section.get("evidence")
    ):
        errors.append("missing_explainability")
    if not section.get("confidence"):
        errors.append("missing_confidence")
    probs = section.get("probabilities")
    if probs is not None:
        total = float(probs.get("bull") or 0) + float(probs.get("base") or 0) + float(probs.get("bear") or 0)
        if abs(total - 100.0) > 0.2:
            errors.append("probabilities_not_100")
    if errors:
        return {"ok": False, "status": "REJECT", "errors": errors}
    return {"ok": True, "status": "PASS", "errors": []}


def validate_pack(pack: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    modules = pack.get("modules") or pack.get("sections") or {}
    if not modules:
        errors.append("no_modules")
    for name, sec in modules.items():
        if name in {"confidence", "history", "accuracy"}:
            continue
        gate = validate_section(sec)
        if not gate["ok"]:
            errors.append(f"{name}:{','.join(gate['errors'])}")
    quality = pack.get("forecast_quality") or {}
    if quality.get("recommendation") or quality.get("investment_rating") or quality.get("target_price"):
        errors.append("recommendation_forbidden")
    if pack.get("recommendation") or pack.get("investment_rating") or pack.get("target_price"):
        errors.append("recommendation_forbidden")
    inputs = pack.get("inputs_present") or {}
    if not inputs.get("financials_annual"):
        errors.append("insufficient_statements")
    readiness = pack.get("data_readiness")
    if isinstance(readiness, dict) and not readiness.get("forecast_ready", False):
        failures = readiness.get("failures") or ["readiness_unknown"]
        errors.extend(f"data_readiness:{item}" for item in failures[:8])
    if errors:
        return {"ok": False, "status": "REJECT", "errors": errors[:40]}
    return {"ok": True, "status": "PASS", "errors": []}
