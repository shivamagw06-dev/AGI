"""Coverage Score breakdown — meaningful Daily Health components."""

from __future__ import annotations

from typing import Any


def coverage_score(ticker: str) -> dict[str, Any]:
    """Per-company coverage score with component percentages."""
    e = ticker.upper()
    components = {
        "identity": 0.0,
        "historical": 0.0,
        "accounting": 0.0,
        "risk": 0.0,
        "timeline": 0.0,
        "evidence": 0.0,
        "sector": 0.0,
        "macro": 0.0,
    }
    try:
        from knowledge_factory.institutional_depth import institutional_depth_checklist
        from knowledge_factory.coverage import _company_checklist

        depth = institutional_depth_checklist(e)
        checks = depth.get("checks") or {}
        base = _company_checklist(e)
        b = base.get("checks") or {}

        components["identity"] = 100.0 if checks.get("identity") else 0.0
        components["historical"] = 100.0 if checks.get("historical_financials") else 0.0
        if checks.get("historical_valuation"):
            components["historical"] = max(components["historical"], 90.0)
        components["accounting"] = 100.0 if checks.get("derived_metrics") else 0.0
        components["risk"] = 100.0 if b.get("risk") else 0.0
        components["timeline"] = 100.0 if checks.get("timeline") or b.get("timeline") else 0.0
        components["evidence"] = float(depth.get("evidence_quality") or 0.0) if checks.get("evidence_pack") else 0.0
        components["sector"] = 100.0 if checks.get("sector_links") else 0.0
        components["macro"] = 100.0 if checks.get("macro_links") else 0.0
    except Exception:
        pass

    score = round(sum(components.values()) / len(components), 2) if components else 0.0
    return {
        "ticker": e,
        "coverage_score": score,
        "components": {k: round(v, 2) for k, v in components.items()},
        "fabricated": False,
    }
