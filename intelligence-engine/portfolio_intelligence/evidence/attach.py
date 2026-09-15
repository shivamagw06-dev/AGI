"""Evidence pack — portfolio conclusions must be evidence-backed."""

from __future__ import annotations

from typing import Any


def evidence_pack(
    *,
    portfolio_id: str,
    holdings: list[dict[str, Any]],
    soft_sources: list[str],
    confidence: dict[str, Any],
) -> dict[str, Any]:
    refs = [
        {
            "claim": f"Portfolio book {portfolio_id} with {len(holdings)} holdings",
            "source": "portfolio_intelligence.portfolio.packs",
            "evidence_tier": 2,
        }
    ]
    for s in soft_sources:
        refs.append({"claim": f"Soft input: {s}", "source": s, "evidence_tier": 2})
    for h in holdings[:8]:
        refs.append(
            {
                "claim": f"{h.get('ticker')} weight {h.get('weight')} · thesis: {h.get('thesis')}",
                "source": "holdings_engine",
                "evidence_tier": 2,
            }
        )
    return {
        "count": len(refs),
        "refs": refs,
        "rule": "No portfolio suitability opinion without holdings + quality evidence hooks",
        "missing": confidence.get("unknowns") or [],
    }
