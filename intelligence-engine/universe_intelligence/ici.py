"""Institutional Coverage Index (ICI) — weighted institutional readiness score.

Stronger operational metric than binary "covered YES/NO".
"""

from __future__ import annotations

from typing import Any

from universe_intelligence.schema import ICI_WEIGHTS


def _component_scores(ticker: str) -> dict[str, float]:
    """0–100 component scores soft-read from KF / depth / risk."""
    e = ticker.upper()
    scores = {k: 0.0 for k in ICI_WEIGHTS}

    try:
        from knowledge_factory.institutional_depth import institutional_depth_checklist

        depth = institutional_depth_checklist(e)
        checks = depth.get("checks") or {}
        identity = depth.get("identity") or {}

        scores["identity"] = 100.0 if checks.get("identity") else (50.0 if identity.get("sector") else 0.0)
        hist_years = float(depth.get("history_years") or 0)
        scores["historical_depth"] = min(100.0, (hist_years / 20.0) * 100.0) if checks.get("historical_financials") else 0.0
        if checks.get("historical_valuation"):
            scores["historical_depth"] = max(scores["historical_depth"], 80.0)
            if hist_years >= 10:
                scores["historical_depth"] = max(scores["historical_depth"], 90.0)
            if hist_years >= 20:
                scores["historical_depth"] = 100.0

        fin = 0.0
        for k, w in (("derived_metrics", 40.0), ("historical_valuation", 30.0), ("peer_intelligence", 30.0)):
            if checks.get(k):
                fin += w
        scores["financial_intelligence"] = fin

        scores["sector_intelligence"] = 100.0 if checks.get("sector_links") else 0.0
        scores["macro_intelligence"] = 100.0 if checks.get("macro_links") else 0.0

        # Risk from base checklist
        try:
            from knowledge_factory.coverage import _company_checklist

            base = _company_checklist(e)
            scores["risk_intelligence"] = 100.0 if (base.get("checks") or {}).get("risk") else 0.0
            timeline_ok = (base.get("checks") or {}).get("timeline")
            if timeline_ok and scores["financial_intelligence"] < 100:
                scores["financial_intelligence"] = min(100.0, scores["financial_intelligence"] + 10.0)
        except Exception:
            scores["risk_intelligence"] = 0.0

        eq = float(depth.get("evidence_quality") or 0.0)
        scores["evidence_packs"] = eq if checks.get("evidence_pack") else 0.0
        scores["portfolio_readiness"] = 100.0 if checks.get("portfolio_readiness") else 0.0
        scores["decision_readiness"] = 100.0 if checks.get("decision_readiness") else 0.0
    except Exception:
        pass

    return {k: round(float(v), 2) for k, v in scores.items()}


def institutional_coverage_index(ticker: str) -> dict[str, Any]:
    e = ticker.upper()
    components = _component_scores(e)
    ici = round(sum(components[k] * ICI_WEIGHTS[k] for k in ICI_WEIGHTS), 2)
    band = (
        "institutional"
        if ici >= 95
        else "strong"
        if ici >= 90
        else "adequate"
        if ici >= 80
        else "needs_improvement"
        if ici >= 60
        else "insufficient"
    )
    return {
        "ticker": e,
        "ici": ici,
        "band": band,
        "components": components,
        "weights": dict(ICI_WEIGHTS),
        "north_star_metric": "institutional_coverage_index",
        "fabricated": False,
    }


def ici_leaderboard(tickers: list[str], *, top: int = 20) -> dict[str, Any]:
    rows = [institutional_coverage_index(t) for t in tickers]
    rows.sort(key=lambda r: (-r["ici"], r["ticker"]))
    return {
        "n": len(rows),
        "top": rows[:top],
        "bottom": list(reversed(rows[-min(top, len(rows)) :])) if rows else [],
        "avg_ici": round(sum(r["ici"] for r in rows) / len(rows), 2) if rows else 0.0,
        "fabricated": False,
    }
