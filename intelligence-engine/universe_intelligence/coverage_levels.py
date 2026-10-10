"""Coverage Levels 0–7 — only Level 7 counts as Institutional Coverage."""

from __future__ import annotations

from typing import Any

from universe_intelligence.schema import (
    COVERAGE_LEVELS,
    INSTITUTIONAL_COVERAGE_LEVEL,
    coverage_level_name,
)


def _soft_signals(ticker: str) -> dict[str, bool]:
    """Soft-read Knowledge Factory / institutional depth — never mutate KF."""
    e = ticker.upper()
    signals = {
        "discovered": True,  # queried ⇒ discovered
        "identity": False,
        "financials": False,
        "historical": False,
        "sector": False,
        "macro": False,
        "evidence_packs": False,
        "decision_ready": False,
    }
    try:
        from knowledge_factory.institutional_depth import institutional_depth_checklist

        depth = institutional_depth_checklist(e)
        checks = depth.get("checks") or {}
        signals["identity"] = bool(checks.get("identity"))
        signals["financials"] = bool(checks.get("historical_financials") or checks.get("derived_metrics"))
        signals["historical"] = bool(checks.get("historical_financials") and checks.get("historical_valuation"))
        signals["sector"] = bool(checks.get("sector_links"))
        signals["macro"] = bool(checks.get("macro_links"))
        signals["evidence_packs"] = bool(checks.get("evidence_pack"))
        signals["decision_ready"] = bool(checks.get("decision_readiness") and depth.get("institutional_depth_ready"))
    except Exception:
        try:
            from institutional_reasoning.fundamentals.primitives import has_primitives
            from knowledge_factory.fixtures.seed import sector_map

            signals["identity"] = bool(sector_map().get(e))
            signals["financials"] = bool(has_primitives(e))
        except Exception:
            pass
    return signals


def coverage_level_for(ticker: str) -> dict[str, Any]:
    """Compute Level 0–7. Institutional Coverage = Level 7 only."""
    e = ticker.upper()
    sig = _soft_signals(e)
    level = 0
    if sig["identity"]:
        level = 1
    if level >= 1 and sig["financials"]:
        level = 2
    if level >= 2 and sig["historical"]:
        level = 3
    if level >= 3 and sig["sector"]:
        level = 4
    if level >= 4 and sig["macro"]:
        level = 5
    if level >= 5 and sig["evidence_packs"]:
        level = 6
    if level >= 6 and sig["decision_ready"]:
        level = 7

    return {
        "ticker": e,
        "coverage_level": level,
        "coverage_level_name": coverage_level_name(level),
        "institutional_coverage": level >= INSTITUTIONAL_COVERAGE_LEVEL,
        "signals": sig,
        "levels": COVERAGE_LEVELS,
        "rule": "Only Level 7 (decision_ready) counts as Institutional Coverage.",
        "fabricated": False,
    }
