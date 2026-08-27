"""Business Quality Report (BQR) — sections 1–13."""

from __future__ import annotations

from typing import Any

from business_quality.engine import build_quality_pack
from business_quality.schema import (
    ISSUES_RECOMMENDATIONS,
    PILLAR_BALANCE,
    PILLAR_CAPITAL,
    PILLAR_CASH,
    PILLAR_EXECUTION,
    PILLAR_GROWTH,
    PILLAR_MODEL,
    PILLAR_PROFIT,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REPORT_SECTIONS,
    SPEC,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _pillar_section(name: str, finding: dict[str, Any] | None) -> dict[str, Any]:
    finding = finding or {}
    return {
        "section": name,
        "pillar": finding.get("pillar"),
        "score": finding.get("score"),
        "confidence": finding.get("confidence"),
        "evidence": finding.get("evidence") or [],
        "supporting_modules": finding.get("supporting_modules") or [],
        "narrative": finding.get("narrative"),
        "uses_llm": False,
    }


def build_report(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = kwargs.pop("pack", None) or build_quality_pack(ticker, **kwargs)
    pillars = pack.get("pillars") or {}
    overall = pack.get("overall") or {}
    score = overall.get("overall_score")

    if score is None:
        overall_prose = (
            "Overall Business Quality Score unavailable — insufficient pillar evidence. "
            "No recommendation is issued."
        )
    else:
        overall_prose = (
            f"Overall Business Quality Score {score} derived from weighted pillar scores "
            f"(weights source: {overall.get('weights_source')}). "
            "Pillar scores are primary. No recommendation is issued."
        )

    # Evidence references across pillars
    refs: list[dict[str, Any]] = []
    for pid, finding in pillars.items():
        for e in finding.get("evidence") or []:
            refs.append({"pillar_id": pid, "pillar": finding.get("pillar"), **e})

    sections: dict[str, Any] = {
        "executive_summary": {
            "section": "executive_summary",
            "quality_score": score,
            "pillar_scores": pack.get("pillar_scores"),
            "strengths_n": len(pack.get("strengths") or []),
            "weaknesses_n": len(pack.get("weaknesses") or []),
            "note": "Synthesis of existing FIRE evidence only — not an investment thesis.",
            "uses_llm": False,
        },
        "overall_quality": {
            "section": "overall_quality",
            "overall": overall,
            "prose": overall_prose,
            "pillars_primary": True,
            "uses_llm": False,
        },
        "growth_quality": _pillar_section("growth_quality", pillars.get(PILLAR_GROWTH)),
        "profitability_quality": _pillar_section("profitability_quality", pillars.get(PILLAR_PROFIT)),
        "cash_quality": _pillar_section("cash_quality", pillars.get(PILLAR_CASH)),
        "balance_sheet_quality": _pillar_section("balance_sheet_quality", pillars.get(PILLAR_BALANCE)),
        "capital_allocation": _pillar_section("capital_allocation", pillars.get(PILLAR_CAPITAL)),
        "management_execution": _pillar_section("management_execution", pillars.get(PILLAR_EXECUTION)),
        "business_model": _pillar_section("business_model", pillars.get(PILLAR_MODEL)),
        "strengths": {
            "section": "strengths",
            "items": pack.get("strengths") or [],
            "n": len(pack.get("strengths") or []),
            "note": "Pillars with comparatively higher evidence-backed scores.",
            "uses_llm": False,
        },
        "weaknesses": {
            "section": "weaknesses",
            "items": pack.get("weaknesses") or [],
            "n": len(pack.get("weaknesses") or []),
            "note": "Pillars with comparatively lower evidence-backed scores — not investment labels.",
            "uses_llm": False,
        },
        "confidence": {
            "section": "confidence",
            **(pack.get("confidence") or {}),
            "uses_llm": False,
        },
        "evidence_references": {
            "section": "evidence_references",
            "n": len(refs),
            "references": refs[:200],
            "inputs": pack.get("inputs"),
            "uses_llm": False,
        },
    }
    for name in REPORT_SECTIONS:
        sections.setdefault(name, {"section": name, "uses_llm": False})

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "report_type": "BusinessQualityReport",
        "report_code": "BQR",
        "sections": sections,
        "pillars": pillars,
        "pillar_scores": pack.get("pillar_scores"),
        "findings": pack.get("findings"),
        "overall": overall,
        "quality_score": score,
        "strengths": pack.get("strengths"),
        "weaknesses": pack.get("weaknesses"),
        "confidence": pack.get("confidence"),
        "mission_control": pack.get("mission_control"),
        "weights": pack.get("weights"),
        "language_guard_violations": pack.get("language_guard_violations") or [],
        "inputs": pack.get("inputs"),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "valuation": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "fire_05_unchanged": True,
        "spec": SPEC,
        "as_of": now_iso(),
    }
