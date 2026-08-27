"""P5.6 Institutional Daily Brief — morning / midday / closing / weekend / monthly."""

from __future__ import annotations

from typing import Any

from investment_operations.schema import BRIEF_TYPES
from investment_operations.util import now_iso, today


def build_daily_brief(
    morning: dict[str, Any],
    research_queue: dict[str, Any],
    portfolio: dict[str, Any],
    alerts: dict[str, Any],
    *,
    brief_type: str = "morning",
) -> dict[str, Any]:
    bt = (brief_type or "morning").lower().strip()
    if bt not in BRIEF_TYPES:
        bt = "morning"

    top = (morning.get("top_opportunities") or [])[:5]
    overnight = (morning.get("overnight_changes") or [])[:5]
    risks = []
    for a in (alerts.get("alerts") or [])[:8]:
        if a.get("type") in {"contradiction", "monitoring", "knowledge_delta"}:
            risks.append(a)

    body = {
        "market": morning.get("market_summary"),
        "macro": morning.get("macro_updates"),
        "top_opportunities": top,
        "new_risks": risks or morning.get("new_contradictions") or [],
        "top_movers": overnight,
        "portfolio_alerts": portfolio.get("research_required") or morning.get("portfolio_alerts") or [],
        "catalysts": (morning.get("catalysts") or [])[:8],
        "theme_changes": morning.get("theme_changes") or [],
        "sector_rotation": morning.get("sector_rotation") or [],
        "research_queue_size": research_queue.get("n"),
        "confidence_changes": [
            {
                "ticker": t.get("ticker"),
                "score": t.get("score"),
                "priority": t.get("research_priority"),
            }
            for t in top
        ],
    }

    title = {
        "morning": "Morning Brief",
        "midday": "Mid-Day Brief",
        "closing": "Closing Brief",
        "weekend": "Weekend Review",
        "monthly": "Monthly Research Review",
    }[bt]

    summary_bits = [
        f"{len(top)} top opportunities",
        f"{len(overnight)} overnight deltas",
        f"{research_queue.get('n') or 0} research tasks",
        f"{len(portfolio.get('research_required') or [])} portfolio reviews",
    ]

    return {
        "brief_type": bt,
        "title": title,
        "session_date": today(),
        "generated_at": now_iso(),
        "headline": f"{title} — " + "; ".join(summary_bits),
        "sections": body,
        "meaningful_only": True,
        "issues_recommendations": False,
    }


def build_all_briefs(
    morning: dict[str, Any],
    research_queue: dict[str, Any],
    portfolio: dict[str, Any],
    alerts: dict[str, Any],
) -> dict[str, Any]:
    return {
        bt: build_daily_brief(morning, research_queue, portfolio, alerts, brief_type=bt)
        for bt in BRIEF_TYPES
    }
